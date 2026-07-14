from typing import Any

from energy_cost import Contract
from fastapi import HTTPException

from cofy import Module
from cofy.api.module import ModuleSettings

from .model import ECContractResponse, MeterType, VerifyMemberRequest
from .source import MemberSource, MemberSourceSettings


class MembersModuleSettings(ModuleSettings):
    type: str = "members"
    source: MemberSourceSettings


class MembersModule(Module, settings=MembersModuleSettings):
    type: str = "members"
    type_description: str = "Module for member-related functionalities"

    def __init__(self, *, source: MemberSource, **kwargs):
        self.source: MemberSource = source
        super().__init__(**kwargs)

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
        self.add_api_route(
            "/{member_id}",
            self.get_by_id,
            methods=["GET"],
            summary="Get member by ID",
            response_model=self.source.response_model,
            responses={404: {"description": "Member not found"}},
        )
        self.add_api_route(
            "/{member_id}/contracts/{ean}",
            self.get_contract_history,
            methods=["GET"],
            summary="Get contract history for a specific meter (identified by EAN) belonging to a member",
            response_model=list[ECContractResponse],
            responses={404: {"description": "Member or contract not found"}},
        )

    def get_by_id(self, member_id: str) -> Any:
        member = self.source.get(member_id)
        if member is None:
            raise HTTPException(status_code=404, detail="Member not found")
        return member

    def verify(self, body: VerifyMemberRequest) -> Any:
        member = self.source.verify(body.activation_code)
        if member is None:
            raise HTTPException(status_code=404, detail="Member not found")
        return member

    def get_contract_history(self, member_id: str, ean: str, meter_type: MeterType | None = None) -> list[Contract]:
        member = self.source.get(member_id)
        if member is None:
            raise HTTPException(status_code=404, detail="Member not found")
        history = member.get_contract_history_for_ean(ean, meter_type)
        if history is not None:
            return history
        raise HTTPException(status_code=404, detail="No contract history found for the specified EAN")
