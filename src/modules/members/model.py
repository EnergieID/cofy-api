from pydantic import BaseModel


class Member(BaseModel):
    id: str
    email: str


class VerifyMemberRequest(BaseModel):
    activation_code: str
