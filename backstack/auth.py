import uuid
import importlib
from functools import partial, wraps
from pymemcache.client.base import Client
from sanic_auth import Auth
from authomatic import Authomatic

from .singleton import Singleton
from .config import settings
from .errors import Unauthenticated, Unauthorized


def get_user_model_class():
    if settings.USER_MODEL is None:
        raise AttributeError("USER_MODEL is not configured, please see documentation for ERROR_AUTH_USER_MODEL")
    last_dot_pos = settings.USER_MODEL.rfind(".")
    path = settings.USER_MODEL[:last_dot_pos]
    model_class = settings.USER_MODEL[last_dot_pos+1:]
    module = importlib.import_module(path)
    if hasattr(module, model_class):
        return getattr(module, model_class)
    else:
        raise AttributeError("The configured user model `{}` can not be imported, please see documentation for"
                             " ERROR_AUTH_USER_MODEL".format(settings.USER_MODEL))


class CustomAuth(Auth, metaclass=Singleton):
    __session_store__ = None

    def set_session_store(self, session_store):
        self.__session_store__ = session_store

    def set_auth_token(self, request, auth_token=None):
        auth_header = request.headers.get("authorization", None)
        if auth_header:
            _, auth_token = auth_header.split(" ")
        if auth_token is None:
            auth_token = uuid.uuid4().hex
        self.auth_session_key = auth_token

    def login_user(self, request, user, auth_token=None):
        if auth_token:
            self.set_auth_token(request, auth_token)
        request.session["user"] = self.serialize(user)
        return self.auth_session_key

    def serialize(self, user):
        return user.id

    def load_user(self, token):
        user_model = get_user_model_class()
        return user_model.query().filter(user_model.id == token).first()

    def current_user(self, request):
        if "authorization" in request.headers:
            _, token = request.headers["authorization"].split(" ")
            try:
                user_id = request.session["user"]
            except KeyError:
                return None
            if user_id is not None:
                return self.load_user(int(user_id))
        return None

    def logout_user(self, request):
        del request.session["user"]


auth = CustomAuth()


authomatic_config = {
    "facebook": {  # Provider name.
        "class_": "authomatic.providers.oauth2.Facebook",  # Provider class. Don"t miss the trailing underscore!

        # Provider type specific keyword arguments:
        "short_name": 1,  # Unique value used for serialization of credentials only needed by OAuth 2.0 and OAuth 1.0a.
        "consumer_key": settings.FACEBOOK_CONSUMER_KEY,  # Key assigned to consumer by the provider.
        "consumer_secret": settings.FACEBOOK_CONSUMER_SECRET,  # Secret assigned to consumer by the provider.
        "scope": [
            # "user_about_me",  # List of requested permissions only needed by OAuth 2.0.
            "email"
        ]
    },

    "google": {
        "class_": "authomatic.providers.oauth2.Google",  # Can be a fully qualified string path.

        # Provider type specific keyword arguments:
        "short_name": 2,  # use authomatic.short_name() to generate this automatically
        "consumer_key": settings.GOOGLE_CONSUMER_KEY,
        "consumer_secret": settings.GOOGLE_CONSUMER_SECRET,
        "scope": [
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email"
        ]
    }
}


def get_authomatic():
    return Authomatic(authomatic_config, settings.SECRET_KEY)


def login_required(func):
    """
    This is a decorator that can be applied to a Controller method that needs a logged in user.
    The inner method receives the Controller instance and checks if the user is logged in
    using the `request.is_authenticated` Boolean on the Controller instance

    :param func: The is the function being decorated.
    :return: Either the method that is decorated (if user is logged in) else `unauthenticated` response (HTTP 401).
    """
    def inner(controller_obj, *args, **kwargs):
        if controller_obj.request.is_authenticated:
            return func(controller_obj, *args, **kwargs)
        else:
            raise Unauthenticated()

    inner.__decorated__ = "login_required"
    return inner


def owner_required(func=None, field_to_check=None):
    """
    This is a decorator that can be applied to a Controller method that needs to test the ownership of
    an object before allowing a succesful response. It first checks if the user is logged in and
    then goes ahead to check if the object is owned by the current user.

    The current object is fetched using the Controller instance's `get_item` method.
    It is assumed that the item has a property `created_by_id` and this should match the `id` of the
    `request.user`.

    :param func: The is the function being decorated.
    :param str field_to_check: Use this to specify that returns the owner of the model if it is not created_by_id
    :return: Either the method that is decorated (if user is logged in and owner). If the user is not
        logged in then the return is a `unauthenticated` response (HTTP 401). If the user is not the owner then
        the return is a `unauthorized` response (HTTP 403).
    """
    if func is None:
        return partial(owner_required, field_to_check=field_to_check)

    @wraps(func)
    def inner(controller_obj, *args, **kwargs):
        if field_to_check is not None:
            owner_id = getattr(controller_obj.get_item(), field_to_check)
        else:
            owner_id = controller_obj.get_item().created_by_id

        if controller_obj.request.is_authenticated:
            if owner_id == controller_obj.request.user.id:
                return func(controller_obj, *args, **kwargs)
            else:
                raise Unauthorized()
        else:
            raise Unauthenticated()

    inner.__decorated__ = "owner_required"
    return inner


def admin_required(func):
    def inner(controller_obj, *args, **kwargs):
        if controller_obj.request.is_authenticated:
            if controller_obj.request.user.is_admin:
                return func(controller_obj, *args, **kwargs)
            else:
                raise Unauthorized()
        else:
            raise Unauthenticated()

    inner.__decorated__ = "admin_required"
    return inner


def permission_check_required(func):
    def inner(controller_obj, *args, **kwargs):
        if controller_obj.permission_check():
            return func(controller_obj, *args, **kwargs)
        else:
            raise Unauthorized()

    inner.__decorated__ = "permission_check_required"
    return inner
