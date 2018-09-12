import importlib
import argparse

from .db import db, Base
from .config import settings


class Commands(object):
    __app = None
    __args = None

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
    def workers():
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
        result = channel.queue_declare(exclusive=True)
        queue_name = result.method.queue

        # Search for workers.setup_workers in all apps
        for app in settings.APPS:
            try:
                fixtures = importlib.import_module("apps.%s.workers" % app)
                if hasattr(fixtures, "setup_workers"):
                    workers = fixtures.setup_workers()
                    for binding in workers:
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

    def execute(self):
        parser = argparse.ArgumentParser(description="default backend")
        parser.add_argument(
            "action",
            action="store",
            choices=["server", "drop_tables", "create_tables", "load_fixtures", "run_workers", "shell"]
        )

        args = parser.parse_args()
        self.__args = args

        if args.action == "server":
            self.__app.go_fast(**settings.DAEMON)
        elif args.action == "drop_tables":
            self.drop_tables()
        elif args.action == "create_tables":
            self.create_tables()
        elif args.action == "load_fixtures":
            self.load_fixtures()
        elif args.action == "run_workers":
            self.workers()
        elif args.action == "shell":
            import code
            code.interact(local=locals())
