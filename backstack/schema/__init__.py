import ujson
from marshmallow import post_load, Schema
from marshmallow_jsonapi import Schema as JSONSchema, SchemaOpts
from marshmallow_jsonapi.fields import DocumentMeta

from . import fields


# Create a nameless class to prevent storing the class in marshmallow"s
# in-memory registry
PaginationSchema = type(str(""), (Schema,), {"metadata": DocumentMeta()})


class DefaultOptions(SchemaOpts):
    """Override schema default options."""

    def __init__(self, meta, *args, **kwargs):
        super().__init__(meta, *args, **kwargs)
        # marshmallow options
        self.strict = True
        self.dateformat = getattr(meta, "dateformat", "iso")
        self.json_module = ujson
        self.ordered = True

        # marshmallow-jsonapi options
        self.type_ = getattr(meta, "type_", None)
        self.inflect = getattr(meta, "inflect", lambda x: x.replace("_", "-"))
        self.self_url = getattr(meta, "self_url", None)
        self.self_url_kwargs = getattr(meta, "self_url_kwargs", None)
        self.self_url_many = getattr(meta, "self_url_many", None)


class SystemSchema(JSONSchema):
    __instance__ = None

    id = fields.Integer(dump_only=True)
    metadata = DocumentMeta()

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

    @staticmethod
    def _page_link_url(request, page_value):
        base_url = request.url.split("?")[0]
        query_args = {
            **request.raw_args,
            "page[number]": page_value,
        }
        query_string = "&".join([
            "{}={}".format(k, v) for k, v in query_args.items()
        ])
        return "{}?{}".format(base_url, query_string)

    def _pagination_links(self, pagination_obj, request):
        # TODO: Use request.app.url_for when endpoint is added to request.
        # https://github.com/channelcat/sanic/pull/979
        self_ = request.url

        first_page = self._page_link_url(request, 1)
        last_page = self._page_link_url(request, pagination_obj.pages)
        prev_page = None
        next_page = None

        if pagination_obj.has_prev:
            prev_page = self._page_link_url(request, pagination_obj.prev_num)

        if pagination_obj.has_next:
            next_page = self._page_link_url(request, pagination_obj.next_num)

        return {
            "self": self_,
            "first": first_page,
            "prev": prev_page,
            "next": next_page,
            "last": last_page
        }

    def paginate_dump(self, pagination_obj, request):
        result = PaginationSchema(strict=True).dump(pagination_obj)

        data = getattr(pagination_obj, "items", [])

        result.data["data"] = self.dump(data, many=True)[0]["data"]
        result.data["links"] = self._pagination_links(pagination_obj, request)
        return result


class BaseSchema(SystemSchema):
    created_by_id = fields.Integer(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    created_from = fields.String(dump_only=True)
