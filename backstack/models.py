import ujson as json
from sqlalchemy import Column, DateTime, Integer, ForeignKey, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql import INET

from .db import db, Base
from .errors import Errors, UniqueConstraintError, RequiredColumnError, ModelError


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
            try:
                setattr(self, obj[0], obj[1])
            except AttributeError as e:
                raise

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
            if (err.orig and err.orig.diag and err.orig.diag.message_primary and
                "null value in column" in err.orig.diag.message_primary):
                raise RequiredColumnError(err.orig.diag.message_primary)
            elif (err.orig and err.orig.diag and err.orig.diag.message_detail and
                "is not present in table" in err.orig.diag.message_detail):
                # 'Key (<column_name>)=(<value>) is not present in table "<related_column>".'
                column_name = err.orig.diag.message_detail.split("=")[0]
                column_name = column_name[column_name.find("(") + 1:-1]
                raise ModelError(field=column_name, message=Errors.INVALID_INPUT.value)
            raise UniqueConstraintError(err.orig.diag.message_detail, err.orig.diag.message_primary)


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
        return Column(Integer, ForeignKey("users.id", name="created_by_fk"), nullable=False)
