from sanic.views import HTTPMethodView

from .errors import NotFound


class BaseController(HTTPMethodView):
    request = None
    kwargs = None
    __request_initiated = False

    def init_request(self, request, *args, **kwargs):
        self.request = request
        self.kwargs = kwargs
        self.__request_initiated = True

    def get(self, request, *args, **kwargs):
        if not self.__request_initiated:
            self.init_request(request, *args, **kwargs)

        if hasattr(self, "handle_get"):
            return self.handle_get(*args, **kwargs)
        else:
            raise NotFound()

    def post(self, request, *args, **kwargs):
        if not self.__request_initiated:
            self.init_request(request, *args, **kwargs)

        if hasattr(self, "handle_post"):
            return self.handle_post(*args, **kwargs)
        else:
            raise NotFound()

    def put(self, request, *args, **kwargs):
        if not self.__request_initiated:
            self.init_request(request, *args, **kwargs)

        if hasattr(self, "handle_put"):
            return self.handle_put(*args, **kwargs)
        else:
            raise NotFound()

    def patch(self, request, *args, **kwargs):
        if not self.__request_initiated:
            self.init_request(request, *args, **kwargs)

        if hasattr(self, "handle_patch"):
            return self.handle_patch(*args, **kwargs)
        else:
            raise NotFound()

    def delete(self, request, *args, **kwargs):
        if not self.__request_initiated:
            self.init_request(request, *args, **kwargs)

        if hasattr(self, "handle_delete"):
            return self.handle_delete(*args, **kwargs)
        else:
            raise NotFound()
