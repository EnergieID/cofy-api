from src.shared.module import Module


class DummyModule(Module):
    def __init__(self, name, type_, router=None, metadata=None):
        self._name = name
        self._type = type_
        self._router = router
        self._metadata = metadata or {}

    @property
    def name(self):
        return self._name

    @property
    def type(self):
        return self._type

    @property
    def router(self):
        return self._router

    @property
    def metadata(self):
        return self._metadata
