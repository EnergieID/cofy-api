from src.shared.module import Module


class MembersModule(Module):
    type: str = "members"
    type_description: str = "Module for member-related functionalities"

    def __init__(self, settings: dict, **kwargs):
        super().__init__(settings, **kwargs)
        if "source" not in self.settings:
            raise ValueError("The 'source' setting is required for the MembersModule.")
        self.source = self.settings["source"]

    def init_routes(self):
        # Define your API routes here
        self.add_api_route("/", self.list, methods=["GET"], summary="List members")

    def list(self):
        return self.source.list()
