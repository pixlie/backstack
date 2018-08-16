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
            except ModuleNotFoundError:
                pass

    @staticmethod
    def workers():
        try:
            import pika
        except ImportError:
            raise Exception("You have to install pika to run workers, see documentation for ERROR_WORKERS_PIKA")
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()

        channel.exchange_declare(
            exchange=settings.MQ_EXCHANGE,
            exchange_type="topic"
        )
        channel.queue_declare(exclusive=True)

    def create_schema_ddl(self):
        import inspect
        from sqlalchemy import create_engine
        from sqlalchemy.schema import CreateTable
        from sqlalchemy.dialects import postgresql

        for app in settings.APPS:
            # try:
            #     models = importlib.import_module("apps.%s.models" % app)
            #     for x in inspect.getmembers(models, inspect.isclass):
            #         cls = getattr(models, x[0])
            #         if issubclass(cls, Base) and hasattr(cls, "__tablename__"):
            #             print(CreateTable(cls.__table__).compile(dialect=postgresql.dialect()))
            # except ModuleNotFoundError:
            #     pass
            self.__app.load_models()

            def metadata_dump(sql, *multiparams, **params):
                # print or write to log or file etc
                print(sql.compile(dialect=engine.dialect))

            engine = create_engine(settings.DB_DEFAULT, convert_unicode=True, strategy="mock", executor=metadata_dump)
            Base.metadata.create_all(engine)

    def execute(self):
        parser = argparse.ArgumentParser(description="default backend")
        parser.add_argument(
            "action",
            action="store",
            choices=["server", "drop_tables", "create_tables", "load_fixtures", "run_workers", "create_schema_ddl",
                     "shell"]
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
        elif args.action == "create_schema_ddl":
            self.create_schema_ddl()
        elif args.action == "shell":
            import code
            code.interact(local=locals())
