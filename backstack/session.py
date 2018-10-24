import ujson as json
from pymemcache.client.base import Client

from .config import settings
from .singleton import Singleton


class MemcacheSession(object, metaclass=Singleton):
    """
    This class creates a dict like Session object that uses memcached to store the session
    data for Authomatic social login/registration.
    """
    __session_client__ = None
    __unique_key__ = None
    __original_data__ = {}
    __session_data__ = {}

    def set_session_key(self, unique_key):
        self.__unique_key__ = unique_key
        self.load()

    def session_store(self):
        if not self.__session_client__:
            self.__session_client__ = Client((settings.MEMCACHED_HOST, 11211))
        return self.__session_client__

    def load(self):
        data = self.session_store().get("sess/%s" % self.__unique_key__)
        if data is None:
            self.__session_data__ = {}
            self.__original_data__ = {}
        else:
            self.__session_data__ = json.loads(data)
            self.__original_data__ = json.loads(data)

    def save(self):
        self.session_store().set("sess/%s" % self.__unique_key__, json.dumps(self.__session_data__))

    def get(self, key, default=None):
        try:
            return self.__session_data__[key]
        except KeyError:
            return default

    @property
    def is_dirty(self):
        return True if self.__original_data__ != self.__session_data__ else False

    def __setitem__(self, key, value):
        self.__session_data__[key] = value

    def __getitem__(self, key):
        return self.__session_data__[key]

    def __delitem__(self, key):
        del self.__session_data__[key]
        return True
