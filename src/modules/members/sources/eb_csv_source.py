import csv

from modules.members.models.eb_member import EBMember, EBProduct
from src.modules.members.source import MemberSource


class EBCSVSource(MemberSource[EBMember]):
    members: dict[str, EBMember] = {}

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.members = {}
        with open(file_path) as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                id = row["KLANTNUMMER"]

                if id in self.members:
                    member = self.members[id]
                else:
                    member = EBMember(
                        id=id,
                        email=row["EMAIL"],
                        type=row["KLANTTYPE"],
                        social_tariff=row["RECHTOPSOCIAALTARIEF"] not in (None, ""),
                    )
                    self.members[id] = member

                member.products.append(
                    EBProduct(
                        id=i,
                        member_id=id,
                        name=row["PRODUCT"],
                        ean=int(row["EAN"]),
                        connection_type=row["AANSLUITING"],
                        start_date=row["STARTDATUM"],
                        end_date=row["EINDDATUM"] if row["EINDDATUM"] else None,
                        grid_operator=row["DISTRIBUTIENET"],
                    )
                )

    def list(self) -> list[EBMember]:
        """List all members from the CSV file."""
        return list(self.members.values())
