from cofy import Module, ModuleSettings


class DummyModuleSettings(ModuleSettings):
    type: str = "dummy"


class DummyModule(Module, settings=DummyModuleSettings):
    type: str = "dummy"
    type_description: str = "Dummy module for testing."

    def __init__(self, name: str, **kwargs):
        super().__init__(name=name, **kwargs)

    def init_routes(self):
        self.add_api_route("/hello", self.hello, methods=["GET"])

    def hello(self):
        return f"Hello from DummyModule {self.name}"
