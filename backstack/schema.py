from marshmallow import Schema, post_load
from . import schema_fields as fields


class BaseSchema(Schema):
    id = fields.Integer(dump_only=True)

    created_by_id = fields.Integer(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    created_from = fields.String(dump_only=True)

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop("instance", None)
        super().__init__(*args, **kwargs)

        for k, v in self.fields.items():
            if hasattr(self.instance, k) and isinstance(v, fields.Nested):
                v.schema.instance = getattr(self.instance, k)

    @post_load
    def make_instance(self, data):
        if hasattr(self, "Meta") and hasattr(self.Meta, "model"):
            if self.instance:
                for k, v in data.items():
                    setattr(self.instance, k, v)
                return self.instance
            else:
                return self.Meta.model(**data)
        return data


class SystemSchema(Schema):
    id = fields.Integer(dump_only=True)

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop("instance", None)
        super().__init__(*args, **kwargs)

        for k, v in self.fields.items():
            if hasattr(self.instance, k) and isinstance(v, fields.Nested):
                v.schema.instance = getattr(self.instance, k)

    @post_load
    def make_instance(self, data):
        if hasattr(self, "Meta") and hasattr(self.Meta, "model"):
            if self.instance:
                for k, v in data.items():
                    setattr(self.instance, k, v)
                return self.instance
            else:
                return self.Meta.model(**data)
        return data
