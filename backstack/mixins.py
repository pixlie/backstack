from sanic import response
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, StatementError, DataError
from sqlalchemy.orm.exc import NoResultFound
from marshmallow.exceptions import ValidationError

from .db import db
from .errors import NotFound, ServerError, Errors


class QueryFilter(object):
    """
    This class provides multiple ways to filter a model.

    The `url_parts` is a mapping of the captured elements from the URL that
    should be used to filter the model.
    `url_parts` maps from the URL part to the field name in model

    If `filter_by_creator` is True, and if the model has a `created_by_id`
    then the model is filtered by current user, which is request.user.id
    """
    url_parts = {}
    filter_by_creator = False
    allowed_filters = []
    query_params = {}

    def get_default_filters(self, *args, **kwargs):
        return []

    def get_url_parts_filters(self):
        """
        This method creates a list of SQLAlchemy Model filters that we apply to the queryset (to get an item or list).
        The filter-able fields are specified in the self.url_parts dict().
        Each entry in self.url_parts should specify the field name as in the URL part and then the corresponding Model
            field that we want to query.
        """
        filters = []
        url_parts = self.url_parts
        for k, v in self.kwargs.items():
            if k in url_parts:
                if type(url_parts[k]) is list:
                    for item in url_parts[k]:
                        filters.append(item == self.kwargs[k])
                else:
                    filters.append(url_parts[k] == self.kwargs[k])
        return filters

    def get_query_params_filters(self):
        """
        This method creates a list of SQLAlchemy Model filters that we apply to the queryset (to get an item or list).
        The filter-able fields are specified in the self.query_params dict().
        Each entry in self.query_params should specify the field name as in the URL part and then the corresponding Model
            field that we want to query.
        """
        filters = []
        query_params = self.query_params
        for k,v in self.request.args.items():
            if k in query_params:
                if type(query_params[k]) is list:
                    filters.append(item.in_(self.request.args[k]))
                else:
                    filters.append(query_params[k].in_(self.request.args[k]))
        return filters

    def get_all_filters(self, *args, **kwargs):
        model = self.get_model()
        filters = self.get_default_filters() + self.get_url_parts_filters() + self.get_query_params_filters()

        if self.filter_by_creator and hasattr(model, "created_by_id"):
            filters.append(getattr(model, "created_by_id") == self.request.user.id)
        return filters


class ModelMixin(object):
    model = None
    serializer_class = None

    def get_model(self):
        return self.model

    def get_queryset(self):
        return self.get_model().query().filter(*self.get_all_filters())

    def get_item(self):
        return self.get_queryset().one()

    def has_related(self):
        m = self.get_model()
        fks = [c for c in m.__table__.columns.values() if c.foreign_keys]
        return True if len(fks) else False

    def get_serializer(self, instance=None):
        partial = True if self.request.method == "PATCH" else False
        if instance:
            return self.serializer_class(partial=partial, instance=instance)
        else:
            return self.serializer_class(partial=partial)


class ListMixin(QueryFilter, ModelMixin):
    """
    This mixin is used to get a list of items for a given model.
    """

    def get_queryset(self):
        if hasattr(self, "get_all_filters"):
            return self.get_model().query().filter(*self.get_all_filters())
        else:
            return self.get_model().query()

    def get_list(self):
        try:
            return self.get_queryset().all()
        except DataError:
            db.session.rollback()
            return []

    def handle_get(self, *args, **kwargs):
        return response.json(
            self.get_serializer().dump(self.get_list(), many=True).data
        )


class ViewMixin(QueryFilter, ModelMixin):
    """
    This mixin is used to get a single item for a given model.

    When we are reading an item for any model, we require some filters.
    """

    def handle_get(self, *args, **kwargs):
        try:
            return response.json(
                self.get_serializer().dump(self.get_item()).data
            )
        except NoResultFound:
            raise NotFound()


class CreateMixin(ModelMixin):
    instance = None
    save_creator = True
    related_fields_to_create = None

    def get_insert_defaults(self):
        return {}

    def create_related(self):
        """
        Saves related models of the model that this request is handling.
        Related models should be specified in the schema instance.
        The foreign key relation is maintained.

        Foreign key names are assumed to be ending in "_id" or "_fk"
        """
        m = self.get_model()
        fks = [c for c in m.__table__.columns.values() if c.foreign_keys]
        for c in fks:
            fk = list(c.foreign_keys)[0]
            if c.name[-3:] == "_id" or c.name[-3:] == "_fk":
                name = c.name[:-3]
                if (name in self.related_fields_to_create and
                        hasattr(self.instance, name) and
                        getattr(self.instance, name, None)):
                    fk_instance = getattr(self.instance, name)
                    if(hasattr(fk_instance, "created_from") and self.request.ip):
                        fk_instance.created_from = self.request.ip
                    fk_instance.save(commit=False)
                    # When we use flush, the INSERT query is sent to the
                    # database, but session is not committed now.
                    # The session is committed by the create_instance method
                    # after the parent is also added to session.
                    db.session.flush()
                    fk_id = getattr(fk_instance, fk.column.name)
                    setattr(self.instance, c.name, fk_id)

    def create_instance(self):
        instance = self.instance
        if hasattr(instance, "created_from") and self.request.ip:
            instance.created_from = self.request.ip
        if (self.save_creator and
                hasattr(instance, "created_by_id") and
                instance.created_by_id is None and self.request.user):
            instance.created_by_id = self.request.user.id
        for k, v in self.get_insert_defaults().items():
            setattr(instance, k, v)
        if hasattr(self, "pre_create"):
            self.pre_create()

        if self.related_fields_to_create and self.has_related():
            self.create_related()

        try:
            instance.save(commit=False)
            if hasattr(self, "pre_create_commit"):
                db.session.flush()
                self.pre_create_commit()

            db.session.commit()
            if hasattr(self, "post_create"):
                self.post_create()
            return True
        except AttributeError as error:
            db.session.rollback()
            error = error.args[0]
            raise ServerError({
                "_server": {
                    "__global__": {
                        "error": Errors.SERVER_ERROR.value,
                        "context": error if type(error) == list and "code" in error[0] else None,
                    },
                },
            })
        except DataError as e:
            db.session.rollback()
            # TODO: Usually this is a length mismatch error, handle this
            raise ServerError()
        except StatementError:
            # TODO: Handle SQL type errors (e.g. passing string 'false' for a boolean field)
            db.session.rollback()
            raise ServerError()

    def handle_post(self, *args, **kwargs):
        schema = self.get_serializer()
        try:
            schema_instance = schema.load(self.request.json or {})
        except ValidationError as err:
            raise ServerError(err.messages, status_code=400)

        if schema_instance.errors:
            raise ServerError({
                "_schema": schema_instance.errors
            }, status_code=400)

        self.instance = schema_instance.data
        self.create_instance()
        return response.json(
            schema.dump(self.instance).data,
            status=201
        )


class UpdateMixin(QueryFilter, ModelMixin):
    instance = None
    related_fields_to_update = None
    save_creator = True

    def get_update_defaults(self):
        return {}

    def update_related(self):
        """
        Saves related models of the model that this request is handling.
        Related models should be specified in the schema instance.
        The foreign key relation is maintained.

        If the related model already exists then it is updated,
        else a new instance of the related model is created.

        Foreign key names are assumed to be ending in "_id" or "_fk"
        """
        m = self.get_model()
        fks = [c for c in m.__table__.columns.values() if c.foreign_keys]
        for c in fks:
            fk = list(c.foreign_keys)[0]
            if c.name[-3:] == "_id" or c.name[-3:] == "_fk":
                name = c.name[:-3]
                if (name in self.related_fields_to_update and
                        hasattr(self.instance, name) and
                        getattr(self.instance, name, None)):
                    # This instance may have an PK (id) in case the related
                    # model already existed.
                    fk_instance = getattr(self.instance, name)
                    if(hasattr(fk_instance, "created_from") and self.request.ip):
                        fk_instance.created_from = self.request.ip
                    # SQLAlchemy will generate INSERT or UPDATE depending
                    # on the related models existance.
                    fk_instance.save(commit=False)
                    # The following applies only for new related models.
                    # When we use flush, the INSERT query is sent to the
                    # database, but session is not committed now.
                    # The session is committed by the create_instance method
                    # after the parent is also added to session.
                    db.session.flush()
                    fk_id = getattr(fk_instance, fk.column.name)
                    setattr(self.instance, c.name, fk_id)

    def update_instance(self):
        instance = self.instance
        if (self.save_creator and
                hasattr(instance, "updated_by_id") and
                instance.updated_by_id is None and self.request.user):
            instance.updated_by_id = self.request.user.id
        for k, v in self.get_update_defaults().items():
            setattr(instance, k, v)

        try:
            if self.related_fields_to_update and self.has_related():
                self.update_related()
        except AssertionError:
            db.session.rollback()
            raise ServerError()
        except StatementError:
            # TODO: Handle SQL type errors (e.g. passing string 'false' for a boolean field)
            db.session.rollback()
            raise ServerError()

        try:
            instance.save(commit=False)
            if hasattr(self, "pre_update_commit"):
                db.session.flush()
                self.pre_update_commit(instance=instance)

            db.session.commit()
            if hasattr(self, "post_update"):
                self.post_update()
            return True
        except AttributeError as error:
            db.session.rollback()
            error = error.args[0]
            raise ServerError({
                "_server": {
                    "__global__": {
                        "error": Errors.SERVER_ERROR.value,
                        "context": error if type(error) == list and "code" in error[0] else None,
                    },
                },
            })
        except DataError:
            db.session.rollback()
            # TODO: Usually this is a length mismatch error, handle this
            raise ServerError()
        except IntegrityError:
            raise ServerError()
        except NoResultFound:
            raise NotFound()

    def handle_put(self, *args, **kwargs):
        try:
            existing = self.get_item()
        except NoResultFound:
            raise NotFound()
        if hasattr(self, "pre_update"):
            self.pre_update(existing=existing, schema=self.get_serializer().load(self.request.json))

        schema = self.get_serializer(instance=existing)

        try:
            schema_instance = schema.load(self.request.json or {})
        except ValidationError as err:
            raise ServerError(message=err.messages, status_code=400)

        if schema_instance.errors:
            raise ServerError({
                "_schema": schema_instance.errors
            }, status_code=400)

        self.instance = schema_instance.data
        self.update_instance()
        return response.json(
            schema.dump(self.instance).data,
            status=200
        )

    def handle_patch(self, *args, **kwargs):
        return self.handle_put(*args, **kwargs)






