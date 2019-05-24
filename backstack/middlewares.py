from .config import settings
from .auth import auth
from .session import MemcacheSession


def session_middlewares(app):
    session_store = MemcacheSession()

    def request_middleware(request):
        session_store.set_session_key(request=request)
        request.session = session_store
        user = auth.current_user(request)
        if user:
            request.user = user
        else:
            request.user = None

    def response_middleware(_, response):
        if session_store.is_dirty:
            session_store.save()
            response.cookies[settings.SESSION_COOKIE_NAME] = session_store.get_session_key()
            response.cookies[settings.SESSION_COOKIE_NAME]["max-age"] = 3600*24*60
        return response

    app.register_middleware(request_middleware, attach_to="request")
    app.register_middleware(response_middleware, attach_to="response")


def cors_middlewares(app):
    def response_middleware(request, response):
        origin = request.headers.get("ORIGIN", None)
        if origin and origin in settings.ALLOWED_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin

    app.register_middleware(response_middleware, attach_to="response")
