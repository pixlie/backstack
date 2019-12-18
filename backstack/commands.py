import importlib
import argparse
from migrate.versioning.shell import main as migrations
from migrate.exceptions import DatabaseAlreadyControlledError

from .db import db, Base
from .config import settings


class Commands(object):
    __app = None
    __args = None
    __app_creator = None
    commands = [
        "server", "load_fixtures", "load_fakes", "run_workers", "shell", "migrations"
    ]

    def __init__(self, app_creator=None):
        if app_creator is not None:
            self.__app_creator = app_creator

    def init_app(self):
        if self.__app_creator is not None:
            self.__app = self.__app_creator()
        else:
            from .app import create_app
            self.__app = create_app()

    @property
    def app(self):
        if self.__app is not None:
            return self.__app
        self.init_app()
        return self.__app

    def load_fixtures(self):
        print("load fixtures")
        self.init_app()
        for app in settings.APPS:
            print(app)
            try:
                fixtures = importlib.import_module("apps.%s.fixtures" % app)
                print("Found fixtures for app {}, running them".format(app))
                if hasattr(fixtures, "generate"):
                    gen = fixtures.generate()
                    if isinstance(gen, dict):
                        model = gen["model"]
                        for data in gen["data"]:
                            model_data = model(**data)
                            model_data.save()
            except ImportError:
                print("App {} does not have fixtures".format(app))

    @staticmethod
    def load_fakes():
        for app in settings.APPS:
            try:
                fakes = importlib.import_module("apps.%s.fakes" % app)
                if hasattr(fakes, "generate"):
                    fakes.generate()
            except ImportError:
                pass

    async def run_workers(self, all_workers):
        import aioamqp
        try:
            transport, protocol = await aioamqp.connect(
                settings.RABBITMQ_HOST,
                settings.RABBITMQ_PORT,
                # loop=self.app.loop
            )
            channel = await protocol.channel()
            await channel.exchange_declare(
                exchange_name=settings.get_mq_exchange_name(),
                type_name="topic",
                durable=True
            )

            for binding in all_workers:
                result = await channel.queue_declare(
                    queue_name=binding[0].__name__,
                    durable=True
                )
                queue_name = result["queue"]

                for key in binding[1]:
                    await channel.queue_bind(
                        exchange_name=settings.get_mq_exchange_name(),
                        queue_name=queue_name,
                        routing_key=key
                    )
                await channel.basic_consume(
                    callback=binding[0],
                    queue_name=queue_name,
                    no_ack=binding[2]
                )
        except aioamqp.AmqpClosedConnection:
            raise Exception("Can not connect to RabbitMQ, please make sure it is running,"
                            " see documentation for ERROR_WORKERS_REQUIREMENTS")

    def manage_workers(self):
        try:
            import asyncio
        except ImportError:
            raise Exception("You have to install asyncio to run workers,"
                            " see documentation for ERROR_WORKERS_REQUIREMENTS")

        try:
            import aioamqp
        except ImportError:
            raise Exception("You have to install aioamqp to run workers,"
                            " see documentation for ERROR_WORKERS_REQUIREMENTS")

        # Search for workers.setup_workers in all apps
        all_workers = []
        self.init_app()
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

        if all_workers is not False:
            # loop = self.app.loop
            loop = asyncio.get_event_loop()
            try:
                loop.run_until_complete(self.run_workers(all_workers=all_workers))
                loop.run_forever()
            except aioamqp.exceptions.ChannelClosed as e:
                if e.code == 404:
                    print("It seems that the RabbitMQ exchange {} does not exist,"
                          " perhaps nothing has been published to it".format(settings.get_mq_exchange_name()))

    def server(self):
        self.app.go_fast(**settings.DAEMON)

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
                self.manage_workers()
            elif args.action == "migrations":
                getattr(self, args.action)(args.sub_commands)
            else:
                getattr(self, args.action)()
