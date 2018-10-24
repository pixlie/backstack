from authomatic.adapters import BaseAdapter
from sanic.response import HTTPResponse
from .config import settings


class CustomAdapter(BaseAdapter):
    """
    This class is the custom adapter for Sanic based backend, implemented as per instructions from:
    https://authomatic.github.io/authomatic/reference/adapters.html
    """
    def __init__(self, request):
        self.request = request
        self.response = HTTPResponse()

    @property
    def params(self):
        return dict((key, value[0]) for key, value in self.request.args.items())

    @property
    def url(self):
        return "{scheme}://{domain}{path}".format(**{
            "scheme": settings.SERVER_PROTOCOL,
            "domain": settings.SERVER_DOMAIN,
            "path": self.request.path
        })

    @property
    def cookies(self):
        return self.request.cookies

    def write(self, value):
        self.response.body = value

    def set_header(self, key, value):
        self.response.headers[key] = value

    def set_status(self, status):
        if status == '302 Found':
            self.response.status = 302
