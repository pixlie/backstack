import importlib
from functools import partial, wraps
from sanic_auth import Auth

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
    def login_user(self, request, user):
        request.session["user"] = self.serialize(user)

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


def get_request_from_controller_or_function_view(controller_or_request):
    """
    Any of our _required functions can be used to decorate either a class based view method or a regular function view.
    We determine what kind of view we are dealing with and extract the request accordingly.
    :param controller_or_request: class based view object or request
    :return: request
    """
    from .controllers import BaseController
    from .app import CustomRequest

    request = None
    if isinstance(controller_or_request, BaseController):
        # If we wrap a method of any inheritor of BaseController, we need the request property of our first param
        request = controller_or_request.request
    elif isinstance(controller_or_request, CustomRequest):
        # If we wrap a regular request handler function then our first param is the request object
        request = controller_or_request
    if request is None:
        raise Unauthenticated()
    return request


def login_required(func):
    """
    This is a decorator that can be applied to a Controller method that needs a logged in user.
    The inner method receives the Controller instance and checks if the user is logged in
    using the `request.is_authenticated` Boolean on the Controller instance

    :param func: The is the function being decorated.
    :return: Either the method that is decorated (if user is logged in) else `unauthenticated` response (HTTP 401).
    """
    def inner(controller_or_request, *args, **kwargs):
        request = get_request_from_controller_or_function_view(controller_or_request)

        if request.is_authenticated:
            return func(controller_or_request, *args, **kwargs)
        else:
            raise Unauthenticated()

    inner.__decorated__ = "login_required"
    return inner


def owner_required(func=None, field_to_check=None):
    """
    This is a decorator that can be applied to a Controller method that needs to allow request to process only if checks
    are successful.

    It checks:
      - if the user is logged in (And)
      - if the object is owned by the current user.

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
    def inner(controller_or_request, *args, **kwargs):
        if field_to_check is not None:
            owner_id = getattr(controller_or_request.get_item(), field_to_check)
        else:
            owner_id = controller_or_request.get_item().created_by_id

        request = get_request_from_controller_or_function_view(controller_or_request)

        if request.is_authenticated:
            if owner_id == request.user.id:
                return func(controller_or_request, *args, **kwargs)
            else:
                raise Unauthorized()
        else:
            raise Unauthenticated()

    inner.__decorated__ = "owner_required"
    return inner


def admin_required(func):
    """
    This is a decorator that can be applied to a Controller method that needs to allow request to process only if checks
    are successful.

    It checks:
      - if the user is logged in (And)
      - if the user is an admin

    The current object is fetched using the Controller instance's `get_item` method.
    It is assumed that the item has a property `created_by_id` and this should match the `id` of the
    `request.user`.

    :param func: The is the function being decorated.
    :param str field_to_check: Use this to specify that returns the owner of the model if it is not created_by_id
    :return: Either the method that is decorated (if user is logged in and owner). If the user is not
        logged in then the return is a `unauthenticated` response (HTTP 401). If the user is not the owner then
        the return is a `unauthorized` response (HTTP 403).
    """

    def inner(controller_or_request, *args, **kwargs):
        request = get_request_from_controller_or_function_view(controller_or_request)

        if request is None:
            return Unauthenticated()
        if request.is_authenticated:
            if request.user.is_admin:
                return func(controller_or_request, *args, **kwargs)
            else:
                raise Unauthorized()
        else:
            raise Unauthenticated()

    inner.__decorated__ = "admin_required"
    return inner


def owner_or_admin_required(func=None, field_to_check=None):
    """
    This is a decorator that can be applied to a Controller method that needs to allow request to process only if checks
    are successful.

    It checks:
      - if the user is logged in (And)
        - (Either) if the object is owned by the current user
        - (Or) if the user is an admin

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
        return partial(owner_or_admin_required, field_to_check=field_to_check)

    @wraps(func)
    def inner(controller_or_request, *args, **kwargs):
        if field_to_check is not None:
            owner_id = getattr(controller_or_request.get_item(), field_to_check)
        else:
            owner_id = controller_or_request.get_item().created_by_id

        request = get_request_from_controller_or_function_view(controller_or_request)

        if request.is_authenticated:
            if owner_id == request.user.id or request.user.is_admin:
                return func(controller_or_request, *args, **kwargs)
            else:
                raise Unauthorized()
        else:
            raise Unauthenticated()

    inner.__decorated__ = "owner_required"
    return inner


def permission_check_required(func):
    def inner(controller_or_request, *args, **kwargs):
        if controller_or_request.permission_check():
            return func(controller_or_request, *args, **kwargs)
        else:
            raise Unauthorized()

    inner.__decorated__ = "permission_check_required"
    return inner
