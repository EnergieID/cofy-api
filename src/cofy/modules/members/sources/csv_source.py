import builtins
import csv

from ..model import Member
from ..source import MemberSource


class MembersCSVSource(MemberSource[Member]):
    def __init__(
        self, file_path: str, id_field: str, email_field: str | None = None, activation_code_field: str | None = None
    ):
        self.members = []
        self.by_activation_code = {}
        with open(file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                member_id = row[id_field]
                email = row[email_field] if email_field else None
                activation_code = row[activation_code_field] if activation_code_field else None

                member = Member(id=member_id, email=email)
                self.members.append(member)
                if activation_code:
                    self.by_activation_code[activation_code] = member

    def list(
        self,
        email: str | None = None,
    ) -> builtins.list[Member]:
        if email is not None:
            return [m for m in self.members if m.email == email]
        return self.members

    def verify(self, activation_code: str) -> Member | None:
        return self.by_activation_code.get(activation_code)
