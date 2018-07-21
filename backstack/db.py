from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from .config import settings
from .singleton import Singleton
from . import constants


class classproperty(object):
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


class DB(metaclass=Singleton):
    __engine = None
    __session_factory = None
    __scoped_session = None

    @property
    def engine(self):
        if self.__engine is None:
            if settings.RUNNING_AS == constants.TEST_MODE:
                self.__engine = create_engine(
                    settings.DB_TEST,
                    convert_unicode=True
                )
            else:
                self.__engine = create_engine(
                    settings.DB_DEFAULT,
                    convert_unicode=True
                )
        return self.__engine

    @property
    def session(self):
        if self.__session_factory is None:
            self.__session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False
            )
        if self.__scoped_session is None:
            self.__scoped_session = scoped_session(self.__session_factory)
        return self.__scoped_session()

    def remove_session(self):
        # A good post about this:
        # http://kronosapiens.github.io/blog/2014/07/29/setting-up-unit-tests-with-flask.html
        if self.__scoped_session is not None:
            self.__scoped_session.remove()

    def test_mode(self):
        settings.RUNNING_AS = constants.TEST_MODE
        self.__engine = None

    def production_mode(self):
        settings.RUNNING_AS = constants.PRODUCTION_MODE
        self.__engine = None

    @property
    def is_test_mode(self):
        return settings.RUNNING_AS == constants.TEST_MODE


db = DB()

Base = declarative_base()
