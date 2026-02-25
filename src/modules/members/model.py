from pydantic import BaseModel


class Member(BaseModel):
    id: str
    email: str | None = None


class VerifyMemberRequest(BaseModel):
    activation_code: str
