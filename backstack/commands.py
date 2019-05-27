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
    def run_workers():
        try:
            import pika
        except ImportError:
            raise Exception("You have to install pika to run workers, see documentation for ERROR_WORKERS_PIKA")
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT
        ))
        channel = connection.channel()

        channel.exchange_declare(
            exchange=settings.RABBITMQ_EXCHANGE,
            exchange_type="topic"
        )

        # Search for workers.setup_workers in all apps
        for app in settings.APPS:
            try:
                workers = importlib.import_module("apps.%s.workers" % app)
                if hasattr(workers, "setup_workers"):
                    workers = workers.setup_workers()
                    for binding in workers:
                        result = channel.queue_declare(exclusive=True)
                        queue_name = result.method.queue
                        for key in binding[1]:
                            channel.queue_bind(
                                exchange=settings.RABBITMQ_EXCHANGE,
                                queue=queue_name,
                                routing_key=key
                            )
                        channel.basic_consume(
                            binding[0],
                            queue=queue_name,
                            no_ack=True
                        )
            except ImportError:
                pass
        channel.start_consuming()

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
            if args.action == "migrations":
                getattr(self, args.action)(args.sub_commands)
            else:
                getattr(self, args.action)()
