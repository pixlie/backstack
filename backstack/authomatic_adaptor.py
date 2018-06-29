from authomatic.adapters import BaseAdapter
from sanic.response import HTTPResponse
from pymemcache.client.base import Client
from .config import settings


class AuthomaticSession(object):
    """
    This class creates a dict like Session object that uses memcached to store the session
    data for Authomatic social login/registration.
    """
    __session_client__ = None

    def session_store(self):
        if not self.__session_client__:
            self.__session_client__ = Client(('localhost', 11211))
        return self.__session_client__

    def save(self):
        pass

    def get(self, key, default=None):
        return self.session_store().get("social-%s" % key, default=default).decode()

    def __setitem__(self, key, value):
        self.session_store().set("social-%s" % key, value)

    def __getitem__(self, key):
        return self.session_store().get("social-%s" % key)

    def __delitem__(self, key):
        return self.session_store().delete("social-%s" % key)


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
