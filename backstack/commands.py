import importlib
import argparse
from migrate.versioning.shell import main as migrations
from migrate.exceptions import DatabaseAlreadyControlledError

from .db import db, Base
from .config import settings


class Commands(object):
    __app = None
    __args = None
    commands = [
        "server", "drop_tables", "create_tables", "load_fixtures", "load_fakes", "run_workers", "shell", "migrations"
    ]

    def __init__(self, app=None):
        if app is None:
            from .app import create_app
            self.__app = create_app()
        else:
            self.__app = app

    def create_tables(self):
        self.__app.load_models()
        Base.metadata.create_all(db.engine)

    @staticmethod
    def drop_tables():
        answer = input("Are you sure you want to run this command. It will "
                       "drop all tables in the database(y/n):")

        if answer == 'y':
            md = Base.metadata
            md.reflect(bind=db.engine)
            md.drop_all(bind=db.engine)

        print("Tables have been droppped successfully")

    @staticmethod
    def load_fixtures():
        for app in settings.APPS:
            try:
                fixtures = importlib.import_module("apps.%s.fixtures" % app)
                if hasattr(fixtures, "generate"):
                    gen = fixtures.generate()
                    if isinstance(gen, dict):
                        model = gen["model"]
                        for data in gen["data"]:
                            model_data = model(**data)
                            model_data.save()
            except ImportError:
                pass

    @staticmethod
    def load_fakes():
        for app in settings.APPS:
            try:
                fakes = importlib.import_module("apps.%s.fakes" % app)
                if hasattr(fakes, "generate"):
                    fakes.generate()
            except ImportError:
                pass

    @staticmethod
    def check_workers():
        try:
            import aioamqp
        except ImportError:
            raise Exception("You have to install aioamqp to run workers,"
                            " see documentation for ERROR_WORKERS_REQUIREMENTS")

        # Search for workers.setup_workers in all apps
        all_workers = []
        for app in settings.APPS:
            try:
                workers = importlib.import_module("apps.%s.workers" % app)
                if hasattr(workers, "setup_workers"):
                    all_workers.append(*workers.setup_workers())
                print("INFO: Worker found in app {}".format(app))
            except ImportError:
                print("INFO: No worker found in app {}".format(app))

        if not all_workers:
            return False

        return all_workers

    @staticmethod
    async def run_workers(all_workers):
        import aioamqp
        try:
            transport, protocol = await aioamqp.connect(settings.RABBITMQ_HOST, settings.RABBITMQ_PORT)
            channel = await protocol.channel()
            exchange_name = settings.RABBITMQ_EXCHANGE
            await channel.exchange_declare(
                exchange_name=exchange_name,
                type_name="topic"
            )

            for binding in all_workers:
                result = await channel.queue_declare(binding[0].__name__, exclusive=True, durable=True)
                queue_name = result["queue"]

                for key in binding[1]:
                    await channel.queue_bind(
                        exchange_name=settings.RABBITMQ_EXCHANGE,
                        queue_name=queue_name,
                        routing_key=key
                    )
                await channel.basic_consume(
                    callback=binding[0],
                    queue_name=queue_name,
                    no_ack=True
                )
        except aioamqp.AmqpClosedConnection:
            raise Exception("Can not connect to RabbitMQ, please make sure it is running,"
                            " see documentation for ERROR_WORKERS_REQUIREMENTS")

    def server(self):
        self.__app.go_fast(**settings.DAEMON)

    @staticmethod
    def migrations(sub_commands):
        try:
            migrations(
                sub_commands,
                repository=settings.DB_MIGRATIONS_FOLDER,
                url=settings.DB_DEFAULT,
                debug="False"
            )
        except DatabaseAlreadyControlledError:
            print("Your database is already under version control for Migrations; nothing to be done.")

    @staticmethod
    def shell():
        import code
        code.interact(local=locals())

    def get_commands(self):
        return self.commands

    def execute(self):
        parser = argparse.ArgumentParser(description="Backstack commands")
        parser.add_argument(
            "action",
            action="store",
            choices=self.get_commands()
        )
        parser.add_argument(
            "sub_commands",
            action="store",
            nargs="*"
        )

        args = parser.parse_args()
        self.__args = args

        if args.action in self.get_commands() and hasattr(self, args.action):
            if args.action == "run_workers":
                try:
                    import asyncio
                except ImportError:
                    raise Exception("You have to install asyncio to run workers,"
                                    " see documentation for ERROR_WORKERS_REQUIREMENTS")

                all_workers = self.check_workers()

                if all_workers is not False:
                    event_loop = asyncio.get_event_loop()
                    event_loop.run_until_complete(self.run_workers(all_workers=all_workers))
                    event_loop.run_forever()
            elif args.action == "migrations":
                getattr(self, args.action)(args.sub_commands)
            else:
                getattr(self, args.action)()
