from decouple import config

from .singleton import Singleton
from . import constants


class Settings(metaclass=Singleton):
    _instance = None

    # Statement for enabling development environment.
    # Keep PRODUCTION = True for production environment
    RUNNING_AS = config("RUNNING_AS", cast=str, default=constants.DEBUG_MODE)

    # Datebase configurations
    DB_DEFAULT = config("DB_DEFAULT", cast=str)
    DB_TEST = config("DB_TEST", cast=str)

    # Settings for running the server on localhost with port number
    DAEMON = {
        "host": config("DAEMON_HOST", cast=str, default="127.0.0.1"),
        "port": config("DAEMON_PORT", cast=int, default=4000),
    }

    SERVER_PROTOCOL = config("SERVER_PROTOCOL", cast=str, default="http")
    SERVER_DOMAIN = config("SERVER_DOMAIN", cast=str, default="localhost:4000")

    WEBSITE_PROTOCOL = config("WEBSITE_PROTOCOL", cast=str, default="http")
    WEBSITE_DOMAIN = config("WEBSITE_DOMAIN", cast=str, default="localhost:3000")

    MANDRILL_API_KEY = config("MANDRILL_API_KEY", cast=str, default="")
    DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", cast=str, default="")
    DEFAULT_FROM_NAME = config("DEFAULT_FROM_NAME", cast=str, default="")
    DEFAULT_SUBJECT_PREFIX = config("DEFAULT_SUBJECT_PREFIX", cast=str, default="")

    SECRET_KEY = config("SECRET_KEY", cast=str)

    RABBITMQ_HOST = config("RABBITMQ_HOST", cast=str, default="amqp://guest:guest@localhost:5672")
    RABBITMQ_EXCHANGE = config("RABBITMQ_EXCHANGE", cast=str, default="mq-exchange")

    FACEBOOK_CONSUMER_KEY = config("FACEBOOK_CONSUMER_KEY", cast=str, default="")
    FACEBOOK_CONSUMER_SECRET = config("FACEBOOK_CONSUMER_SECRET", cast=str, default="")

    GOOGLE_CONSUMER_KEY = config("GOOGLE_CONSUMER_KEY", cast=str, default="")
    GOOGLE_CONSUMER_SECRET = config("GOOGLE_CONSUMER_SECRET", cast=str, default="")

    MEMCACHED_HOST = config("MEMCACHED_HOST", cast=str, default="localhost")

    APPS = ()


settings = Settings()
