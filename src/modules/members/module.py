from src.shared.module import Module


class MembersModule(Module):
    type: str = "members"
    type_description: str = "Module for member-related functionalities"

    def __init__(self, settings: dict, **kwargs):
        if "source" not in settings:
            raise ValueError("The 'source' setting is required for the MembersModule.")
        self.source = settings["source"]
        super().__init__(settings, **kwargs)

    def init_routes(self):
        # Define your API routes here
        self.add_api_route(
            "/", self.source.list, methods=["GET"], summary="List members"
        )
