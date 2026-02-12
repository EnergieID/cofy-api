import csv
import datetime as dt
from typing import Annotated

from fastapi import Query

from src.modules.members.models.eb_member import EBMember, EBProduct
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
                        start_date=dt.datetime.strptime(
                            row["STARTDATUM"], "%d/%m/%Y %H:%M:%S"
                        ).date(),
                        end_date=dt.datetime.strptime(
                            row["EINDDATUM"], "%d/%m/%Y %H:%M:%S"
                        ).date()
                        if row["EINDDATUM"]
                        else None,
                        grid_operator=row["DISTRIBUTIENET"],
                    )
                )

    def list(
        self,
        email: Annotated[
            str | None, Query(description="Filter by email of the member")
        ] = None,
        ean: Annotated[
            int | None, Query(description="Filter by EAN of the product")
        ] = None,
    ) -> list[EBMember]:
        """List all members from the CSV file."""
        return [
            member
            for member in self.members.values()
            if (email is None or member.email == email)
            and (ean is None or any(product.ean == ean for product in member.products))
        ]
