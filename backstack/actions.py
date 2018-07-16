from marshmallow.exceptions import ValidationError
from sanic import response

from .errors import ServerError, Errors


class ModelMixin(object):
    _model = None
    _serializer_class = None

    def get_all_filters(self):
        raise NotImplementedError()

    def get_model(self):
        return self._model

    def get_queryset(self):
        return self.get_model().query().filter(*self.get_all_filters())

    def get_item(self):
        return self.get_queryset().one()

    def has_related(self):
        m = self.get_model()
        fks = [c for c in m.__table__.columns.values() if c.foreign_keys]
        return True if len(fks) else False

    def get_serializer(self, instance=None):
        if instance:
            return self._serializer_class(instance=instance)
        else:
            return self._serializer_class()


class Create(object):
    _endpoint = None
    _instance = None
    _request = None
    _db = None
    _app = None
    _allow = None
    _fields = None

    _save_creator = True
    _related_fields_to_create = None

    def __init__(self, allow=None, fields=None):
        self._allow = allow
        self._fields = fields

    def get_insert_defaults(self):
        return {}

    def has_related(self):
        raise NotImplementedError()

    def get_serializer(self):
        raise NotImplementedError()

    def create_related(self):
        """
        Saves related models of the model that this request is handling.
        Related models should be specified in the schema instance.
        The foreign key relation is maintained.

        Foreign key names are assumed to be ending in "_id" or "_fk"
        """
        endpoint = self._endpoint
        m = endpoint.get_model()
        fks = [c for c in m.__table__.columns.values() if c.foreign_keys]
        for c in fks:
            fk = list(c.foreign_keys)[0]
            if c.name[-3:] == "_id" or c.name[-3:] == "_fk":
                name = c.name[:-3]
                if (name in self._related_fields_to_create and
                        hasattr(self._instance, name) and
                        getattr(self._instance, name, None)):
                    fk_instance = getattr(self._instance, name)
                    if hasattr(fk_instance, "created_from") and self._request.ip:
                        fk_instance.created_from = self._request.ip
                    fk_instance.save(commit=False)
                    # When we use flush, the INSERT query is sent to the
                    # database, but session is not committed now.
                    # The session is committed by the create_instance method
                    # after the parent is also added to session.
                    self._db.session.flush()
                    fk_id = getattr(fk_instance, fk.column.name)
                    setattr(endpoint.instance, c.name, fk_id)

    def create_instance(self):
        instance = self._instance
        if hasattr(instance, "created_from") and self._request.ip:
            instance.created_from = self._request.ip
        if (self._save_creator and
                hasattr(instance, "created_by_id") and
                instance.created_by_id is None and self._request.user):
            instance.created_by_id = self._request.user.id
        for k, v in self.get_insert_defaults().items():
            setattr(instance, k, v)
        if hasattr(self, "pre_create"):
            self.pre_create()

        if self._related_fields_to_create and self.has_related():
            self.create_related()

        try:
            instance.save(commit=False)
            if hasattr(self, "pre_create_commit"):
                self._db.session.flush()
                self.pre_create_commit()

            self._db.session.commit()
            if hasattr(self, "post_create"):
                self.post_create()
            return True
        except AttributeError as error:
            self._db.session.rollback()
            error = error.args[0]
            raise ServerError({
                "_server": {
                    "__global__": {
                        "error": Errors.SERVER_ERROR.value,
                        "context": error if type(error) == list and "code" in error[0] else None,
                    },
                },
            })

    def handle_post(self):
        schema = self.get_serializer()
        try:
            schema_instance = schema.load(self._request.json)
        except ValidationError as err:
            raise ServerError(err.messages, status_code=400)

        if schema_instance.errors:
            raise ServerError({
                "_schema": schema_instance.errors
            }, status_code=400)

        self._instance = schema_instance.data
        self.create_instance()
        return response.json(
            schema.dump(self._instance).data,
            status=201
        )


class Delete(object):
    _allow = None

    def __init__(self, allow=None):
        self._allow = allow
