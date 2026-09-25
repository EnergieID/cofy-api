from cofy.modules.members import Member, MemberSource


class DummyMemberSource(MemberSource[Member]):
    def list(self, email: str | None = None) -> list[Member]:
        return []

    def get(self, member_id: str) -> Member | None:
        return None

    def verify(self, activation_code: str) -> Member | None:
        return None


def test_member_source_default_response_model_is_member():
    assert DummyMemberSource().response_model is Member
