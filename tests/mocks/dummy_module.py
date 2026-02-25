from src.shared.module import Module


class DummyModule(Module):
    type: str = "dummy"
    type_description: str = "Dummy module for testing."

    def __init__(self, name: str):
        super().__init__(name=name)

    def init_routes(self):
        self.add_api_route("/hello", self.hello, methods=["GET"])

    def hello(self):
        return f"Hello from DummyModule {self.name}"
