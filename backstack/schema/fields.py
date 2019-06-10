from marshmallow_jsonapi import fields
from marshmallow.exceptions import ValidationError

from ..errors import Errors


class Defaults:
    __classname__ = "defaults"

    default_error_messages = {
        "required": Errors.REQUIRED_FIELD.value,
        "type": Errors.INVALID_TYPE.value,  # used by Unmarshaller
        "null": Errors.NOT_NULL_FIELD.value,
        "validator_failed": Errors.INVALID_INPUT.value,
        "invalid": Errors.INVALID_INPUT.value,
        "invalid_utf8": Errors.INVALID_INPUT.value,
        "format": "{input} cannot be formatted as a %s." % __classname__
    }


class String(Defaults, fields.String):
    __classname__ = "string"


class Number(Defaults, fields.Number):
    __classname__ = "number"


class Integer(Defaults, fields.Integer):
    __classname__ = "integer"


class Decimal(Defaults, fields.Decimal):
    __classname__ = "decimal"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_error_messages["special"] = "Special numeric values are not permitted."


class Boolean(Defaults, fields.Boolean):
    __classname__ = "boolean"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_error_messages["invalid"] = "Not a valid boolean."


class FormattedString(Defaults, fields.FormattedString):
    __classname__ = "string"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_error_messages["format"] = "Cannot format string with given data."


class DateTime(Defaults, fields.DateTime):
    __classname__ = "datetime"


class Date(Defaults, fields.Date):
    __classname__ = "date"


class Time(Defaults, fields.TimeDelta):
    __classname__ = "time"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_error_messages["format"] = "{input!r} cannot be formatted as timedelta"


class Float(Defaults, fields.Float):
    __classname__ = "float"


class Email(Defaults, fields.Email):
    __classname__ = "email"


class Nested(Defaults, fields.Nested):
    __classname__ = "nested"


class Enum(Defaults, fields.Field):
    __classname__ = "enum"

    def __init__(self, enum, *args, **kwargs):
        self.enum = enum
        super().__init__(*args, **kwargs)

    def _serialize(self, value, attr, obj):
        try:
            return value.value
        except ValueError:
            raise ValidationError(Errors.INVALID_INPUT.value)

    def _deserialize(self, value, attr, data):
        try:
            return self.enum(value)
        except ValueError:
            raise ValidationError(Errors.INVALID_INPUT.value)


class Method(Defaults, fields.Method):
    __classname__ = "method"


class Function(Defaults, fields.Function):
    __classname__ = "function"


class Dict(Defaults, fields.Dict):
    __classname__ = "dict"
