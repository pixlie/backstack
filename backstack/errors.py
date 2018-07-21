from enum import Enum
import re
from sanic.exceptions import SanicException


class Errors(Enum):
    REQUIRED_FIELD = "REQUIRED_FIELD"
    INVALID_TYPE = "INVALID_TYPE"
    NOT_NULL_FIELD = "NOT_NULL_FIELD"
    INVALID_INPUT = "INVALID_INPUT"

    PASSWORD_WEAK = "PASSWORD_WEAK"
    PASSWORD_MISMATCH = "PASSWORD_MISMATCH"

    AUTH_EMAIL_PASSWORD_INVALID = "AUTH_EMAIL_PASSWORD_INVALID"

    NOT_FOUND = "NOT_FOUND"
    SERVER_ERROR = "SERVER_ERROR"

    UNAUTHENTICATED = "UNAUTHENTICATED"
    UNAUTHORIZED = "UNAUTHORIZED"

    DUPLICATE_UNIQUE_VALUE = "DUPLICATE_UNIQUE_VALUE"


class ModelError(Exception):
    field = None
    message = None

    def __init__(self, field, message=None):
        self.field = field
        self.message = message


class UniqueConstraintError(Exception):
    """
    Used when there is a database level exception that a column needs to have Unique entries but the data passed
    for this column already exists.
    """
    field = None

    def __init__(self, message):
        self.field = re.search(r"\([\w\-_]+\)", message.split("=")[0])[0][1:-1]

    def get_error(self):
        error = dict()
        error[self.field] = Errors.DUPLICATE_UNIQUE_VALUE.value
        return error


class RequiredColumnError(Exception):
    """
    Used when there is a database level exception that a column not nullable but no data is passed for it.
    """
    field = None

    def __init__(self, message):
        self.field = message.split("\"")[1]

    def get_error(self):
        error = dict()
        error[self.field] = Errors.REQUIRED_FIELD.value
        return error


class ServerError(SanicException):
    def __init__(self, message=None, status_code=None):
        super().__init__(
            message=message if message is not None else {
                "_server": {
                    "__global__": Errors.SERVER_ERROR.value,
                },
            },
            status_code=status_code if status_code is not None else 400
        )


class NotFound(SanicException):
    def __init__(self, message=None, status_code=None):
        super().__init__(
            message=message if message is not None else {
                "_server": {
                    "__global__": Errors.NOT_FOUND.value,
                },
            },
            status_code=status_code if status_code is not None else 404
        )


class Unauthenticated(SanicException):
    def __init__(self, message=None, status_code=None):
        super().__init__(
            message=message if message is not None else {
                "_server": {
                    "__global__": Errors.UNAUTHENTICATED.value,
                },
            },
            status_code=status_code if status_code is not None else 401
        )


class Unauthorized(SanicException):
    def __init__(self, message=None, status_code=None):
        super().__init__(
            message=message if message is not None else {
                "_server": {
                    "__global__": Errors.UNAUTHORIZED.value,
                },
            },
            status_code=status_code if status_code is not None else 403
        )
