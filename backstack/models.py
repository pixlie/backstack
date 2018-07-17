import ujson as json
from sqlalchemy import Column, DateTime, Integer, ForeignKey, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql import INET

from .db import db, Base
from .errors import UniqueConstraintError


class Serializer(object):
    __table__ = None

    def dump_json(self):
        json.dumps({c.name: getattr(self, c.name) for c in self.__table__.columns})


class Deserializer(object):
    __table__ = None

    def load_json(self, data):
        column_keys = self.__table__.columns.keys()
        for k, v in data.items():
            if k in column_keys:
                setattr(self, k, v)


class SystemModel(Base):
    """
    Inherit from this base model if you do not need any default fields in your inherited class.
    It contains the unique and primary key ID field which is mandatory in all models.
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True)

    def __init__(self, *args, **kwargs):
        for obj in kwargs.items():
            setattr(self, obj[0], obj[1])

    @classmethod
    def query(cls, *args, **kwargs):
        cls.metadata.bind = db.engine
        if args:
            return db.session.query(*args)
        return db.session.query(cls)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def save(self, commit=True):
        db.session.add(self)

        try:
            if commit:
                db.session.commit()
            else:
                db.session.flush()
        except IntegrityError as err:
            db.session.rollback()
            raise UniqueConstraintError(err.orig.diag.message_detail)


class BaseModel(SystemModel):
    """
    This is our base model for all other models that are owned by a user.
    It tracks the user who created any record, when and from which IP address.
    """
    __abstract__ = True

    created_at = Column(DateTime, nullable=False, server_default=text("(now() at time zone 'utc')"))
    created_from = Column(INET, nullable=False)

    @declared_attr
    def created_by_id(self):
        return Column(Integer, ForeignKey("user.id", name="created_by_fk"), nullable=False)