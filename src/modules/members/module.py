from pathlib import Path

from sqlmodel import SQLModel

from src.shared.module import Module


class MembersModule(Module):
    type: str = "members"
    type_description: str = "Module for member-related functionalities"
    uses_database: bool = True
    migration_locations: list[str] = [
        str(Path(__file__).resolve().parent / "migrations" / "versions")
    ]
    target_metadata = SQLModel.metadata

    def __init__(self, settings: dict, **kwargs):
        if "source" not in settings:
            raise ValueError("The 'source' setting is required for the MembersModule.")
        self.source = settings["source"]
        super().__init__(settings, **kwargs)

    def init_routes(self):
        # Define your API routes here
        self.add_api_route(
            "/",
            self.source.list,
            methods=["GET"],
            summary="List members",
            response_model=list[self.source.response_model],
        )
