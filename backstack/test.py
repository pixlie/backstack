from .endpoint import Endpoint
from .actions import Create, Delete


class CurrentUser(object):
    is_active = "check_is_active"
    is_owner = ("CurrentUser", "check_is_owner")
    has_access = ("CurrentUser", "check_has_access")


class RequestedInstance(object):
    # You can use this to perform actions if instance is marked as `archived`
    is_archived = ("RequestedInstance", "check_is_archived")


class RequestedQuery(object):
    def does_not_exist(self):
        # You can use this to trap errors where any requested instance does not exist and use them in some way
        return self.__class__, "does_not_exist"


places = Endpoint(
    url='/places',
    model=Place,
    create=Create(
        allow=CurrentUser.is_active,
    ),
    delete=Delete(
        allow=CurrentUser.is_owner,
    ),
)
