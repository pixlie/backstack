import sys
from decouple import config

from .singleton import Singleton
from . import constants


class Settings(metaclass=Singleton):
    _instance = None

    def __init__(self):
        config.search_path = sys.path[0]

        # Statement for enabling development environment.
        # Keep PRODUCTION = True for production environment
        self.RUNNING_AS = config("RUNNING_AS", cast=str, default=constants.DEBUG_MODE)

        # Python path to the User model class (SQLAlchemy model)
        # This is not read from settings.ini, instead set this in your main.py like
        #  `settings.USER_MODEL = "apps.account.models.User"`
        self.USER_MODEL = None

        # Datebase configurations
        self.DB_DEFAULT = config("DB_DEFAULT", cast=str)
        self.DB_TEST = config("DB_TEST", cast=str)

        # Settings for running the server on localhost with port number
        self.DAEMON = {
            "host": config("DAEMON_HOST", cast=str, default="127.0.0.1"),
            "port": config("DAEMON_PORT", cast=int, default=4000),
        }

        self.SERVER_PROTOCOL = config("SERVER_PROTOCOL", cast=str, default="http")
        self.SERVER_DOMAIN = config("SERVER_DOMAIN", cast=str, default="localhost:4000")

        self.WEBSITE_PROTOCOL = config("WEBSITE_PROTOCOL", cast=str, default="http")
        self.WEBSITE_DOMAIN = config("WEBSITE_DOMAIN", cast=str, default="localhost:3000")

        self.MANDRILL_API_KEY = config("MANDRILL_API_KEY", cast=str, default="")
        self.DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", cast=str, default="")
        self.DEFAULT_FROM_NAME = config("DEFAULT_FROM_NAME", cast=str, default="")
        self.DEFAULT_SUBJECT_PREFIX = config("DEFAULT_SUBJECT_PREFIX", cast=str, default="")

        self.SECRET_KEY = config("SECRET_KEY", cast=str)

        self.RABBITMQ_HOST = config("RABBITMQ_HOST", cast=str, default="amqp://guest:guest@localhost:5672")
        self.RABBITMQ_EXCHANGE = config("RABBITMQ_EXCHANGE", cast=str, default="mq-exchange")

        self.FACEBOOK_CONSUMER_KEY = config("FACEBOOK_CONSUMER_KEY", cast=str, default="")
        self.FACEBOOK_CONSUMER_SECRET = config("FACEBOOK_CONSUMER_SECRET", cast=str, default="")

        self.GOOGLE_CONSUMER_KEY = config("GOOGLE_CONSUMER_KEY", cast=str, default="")
        self.GOOGLE_CONSUMER_SECRET = config("GOOGLE_CONSUMER_SECRET", cast=str, default="")

        self.MEMCACHED_HOST = config("MEMCACHED_HOST", cast=str, default="localhost")

        self.APPS = ()


settings = Settings()