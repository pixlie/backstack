import math
from marshmallow import Schema, post_load
from . import fields


class PaginationSchema(Schema):
    number = fields.Integer()
    size = fields.Integer()
    total_pages = fields.Integer()
    total_count = fields.Integer()


class SystemSchema(Schema):
    __instance__ = None
    __only__ = None
    __exclude__ = ()

    id = fields.Integer(dump_only=True)

    def __init__(self, *args, **kwargs):
        self.__instance__ = kwargs.pop("instance", None)
        self.__only__ = kwargs.get("only", None)
        self.__exclude__ = kwargs.get("exclude", ())

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

    def paginated_dump(self, data):
        class_paginated_schema = type("PaginatedSchema", (Schema, ),  {
            "pagination": fields.Nested(PaginationSchema),
            "data": fields.Nested(data["schema"].__class__, many=True, only=self.__only__, exclude=self.__exclude__)
        })
        return class_paginated_schema().dump({
            "pagination": {
                "number": data["number"],
                "size": data["size"],
                "total_pages": math.ceil(data["count"] / data["size"]),
                "total_count": data["count"]
            },
            "data": data["items"],
        })


class BaseSchema(SystemSchema):
    created_by_id = fields.Integer(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    created_from = fields.String(dump_only=True)
