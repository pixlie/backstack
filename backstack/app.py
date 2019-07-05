from sanic import Sanic
from sanic.request import Request
from sanic.response import json
from sanic.exceptions import SanicException
import importlib

from .singleton import Singleton
from .auth import auth
from .config import settings
from .errors import ModelError
from .middlewares import session_middlewares, cors_middlewares


class MainApp(Sanic, metaclass=Singleton):
    def setup_routes(self):
        for app in settings.APPS:
            try:
                urls = importlib.import_module("apps.%s.urls" % app)
                if hasattr(urls, "setup_routes"):
                    urls.setup_routes(self)
            except ImportError as e:
                print("In app {}:".format(app), e)

    def add_route(self, *args, **kwargs):
        # Prepend /api to all API URLs by default
        prepend = kwargs.pop("prepend", "/api")
        uri = "%s%s" % (prepend, args[1])
        super().add_route(args[0], uri, **kwargs)

    @staticmethod
    def load_models():
        models = []
        for app in settings.APPS:
            models.append(importlib.import_module("apps.%s.models" % app))
        return models


def json_exception(request, exception):
    errors = {}
    status_code = 400

    if isinstance(exception, SanicException):
        status_code = exception.status_code
        if len(exception.args) > 0:
            if hasattr(exception.args[0], "items"):
                for (key, value) in exception.args[0].items():
                    if key == "_model" or key == "_server":
                        for (k, v) in value.items():
                            errors[k] = v
                    elif key == "_schema":
                        # Schema errors come out as a list, we extract the first element
                        for (k, v) in value.items():
                            errors[k] = v[0]

    if isinstance(exception, ModelError):
        errors["_model"] = {}
        errors["_model"][exception.field] = exception.message

    return json(errors, status=status_code)


class CustomRequest(Request):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.session = None
        self.__client_ip = None

    @property
    def is_authenticated(self):
        return self.user is not None

    @property
    def client_ip(self):
        if self.__client_ip is None:
            from sanic_ipware import get_client_ip
            ip, _ = get_client_ip(self)
            if (ip is None):
                ip = "127.0.0.1";
            self.__client_ip = ip
        return self.__client_ip


def create_app(override_settings=None, app_class=MainApp, middlewares=(session_middlewares, cors_middlewares)):
    if override_settings:
        # If override_settings is present, then it is a callable which will override the default settings
        override_settings(settings)
    app = app_class(__name__, request_class=CustomRequest)
    app.config.SECRET_KEY = settings.SECRET_KEY
    auth.setup(app=app)
    for middleware in middlewares:
        middleware(app)
    app.setup_routes()

    app.error_handler.add(SanicException, json_exception)
    app.error_handler.add(ModelError, json_exception)

    return app
