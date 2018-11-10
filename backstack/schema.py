from marshmallow import Schema, post_load
from . import schema_fields as fields


class SystemSchema(Schema):
    __instance__ = None

    id = fields.Integer(dump_only=True)

    def __init__(self, *args, **kwargs):
        self.__instance__ = kwargs.pop("instance", None)
        super().__init__(*args, **kwargs)

        for k, v in self.fields.items():
            if hasattr(self.__instance__, k) and isinstance(v, fields.Nested):
                v.schema.set_instance(getattr(self.__instance__, k))

    @post_load
    def make_instance(self, data):
        if hasattr(self, "Meta") and hasattr(self.Meta, "model"):
            if self.__instance__:
                for k, v in data.items():
                    setattr(self.__instance__, k, v)
                return self.__instance__
            else:
                return self.Meta.model(**data)
        return data

    def set_instance(self, instance):
        self.__instance__ = instance

    def get_instance(self):
        return self.__instance__


class BaseSchema(SystemSchema):
    created_by_id = fields.Integer(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    created_from = fields.String(dump_only=True)
