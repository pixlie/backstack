from .actions import Create, Delete


_possible_actions = {
    "create": Create,
    "read_one": None,
    "read_many": None,
    "update": None,
    "delete": Delete,
}


class Endpoint(object):
    _url = None
    _model = None
    _instance = None

    _create = None
    _read_one = None
    _read_many = None
    _update = None
    _delete = None

    def __init__(self, url, model=None, actions=None, create=None, read_one=None, read_many=None, update=None, delete=None):
        self._url = url
        self._model = model

        if actions:
            for action in actions:
                if action in _possible_actions.keys():
                    setattr(self, "_" + action, _possible_actions[action])
                else:
                    raise Exception("INVALID_ACTION")
        self._create = create
        self._read_one = read_one
        self._read_many = read_many
        self._update = update
        self._delete = delete

    def get_instance(self):
        if self._instance is None:
            self._instance = self._model()
        return self._instance

    def handle_create(self):
        return self._create.execute()

    def handle_read_one(self):
        return self._read_one.execute()

    def handle_read_many(self):
        return self._read_many.execute()

    def handle_update(self):
        return self._update.execute()

    def handle_delete(self):
        return self._delete.execute()
