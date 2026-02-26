from typing import Any

from fastapi import HTTPException

from cofy.module import Module
from cofy.modules.members.model import VerifyMemberRequest
from cofy.modules.members.source import MemberSource


class MembersModule(Module):
    type: str = "members"
    type_description: str = "Module for member-related functionalities"

    def __init__(self, settings: dict, **kwargs):
        if "source" not in settings:
            raise ValueError("The 'source' setting is required for the MembersModule.")
        self.source: MemberSource = settings["source"]
        super().__init__(settings, **kwargs)

    def init_routes(self):
        self.add_api_route(
            "/",
            self.source.list,
            methods=["GET"],
            summary="List members",
            response_model=list.__class_getitem__(self.source.response_model),
        )
        self.add_api_route(
            "/verify",
            self.verify,
            methods=["POST"],
            summary="Verify member activation code",
            response_model=self.source.response_model,
            responses={404: {"description": "Member not found"}},
        )

    def verify(self, body: VerifyMemberRequest) -> Any:
        member = self.source.verify(body.activation_code)
        if member is None:
            raise HTTPException(status_code=404, detail="Member not found")
        return member
