from sanic import Sanic
from sanic.request import Request
from sanic.response import json
from sanic.exceptions import SanicException
import importlib

from .singleton import Singleton
from .auth import auth
from .config import settings
from .errors import ModelError


class MainApp(Sanic, metaclass=Singleton):
    def setup_routes(self):
        for app in settings.APPS:
            try:
                urls = importlib.import_module("apps.%s.urls" % app)
                if hasattr(urls, "setup_routes"):
                    urls.setup_routes(self)
            except ImportError:
                pass

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


def get_session_middleware():
    session_store = {}

    def session_middleware(request):
        request["session"] = session_store
        auth.set_auth_token(request)
        user = auth.current_user(request)
        if user:
            request.user = user
        else:
            request.user = None
    return session_middleware


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

    @property
    def is_authenticated(self):
        return self.user is not None


def create_app(override_settings=None, app_class=MainApp, session_middleware=get_session_middleware):
    if override_settings:
        # If override_settings is present, then it is a callable which will override the default settings
        override_settings(settings)
    app = app_class(__name__, request_class=CustomRequest)
    app.config.SECRET_KEY = settings.SECRET_KEY
    auth.setup(app=app)
    app.register_middleware(session_middleware(), attach_to="request")
    app.setup_routes()

    app.error_handler.add(SanicException, json_exception)
    app.error_handler.add(ModelError, json_exception)

    return app
