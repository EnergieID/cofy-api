from src.shared.module import Module


class DummyModule(Module):
    def __init__(self, name, type_, metadata=None):
        super().__init__({"name": name})
        self._type = type_
        self._metadata = metadata or {}

    def init_routes(self):
        pass

    @property
    def type(self):
        return self._type

    @property
    def metadata(self):
        return self._metadata
