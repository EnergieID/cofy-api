import csv
import datetime as dt

from sqlmodel import Session

from src.modules.members.models.eb_member import (
    EBClientType,
    EBConnectionType,
    EBMember,
    EBProduct,
    GridOperator,
)


class EBLoadFromCSV:
    def __init__(self, file_path: str, db_engine):
        self.file_path = file_path
        self.db_engine = db_engine

    def __call__(self):
        with open(self.file_path) as f, Session(self.db_engine) as session:
            reader = csv.DictReader(f)
            for row in reader:
                id = row["KLANTNUMMER"]

                member = session.get(EBMember, id)

                if member is None:
                    member = EBMember(id=id)
                member.email = row["EMAIL"]
                member.type = EBClientType(row["KLANTTYPE"])
                member.social_tariff = row["RECHTOPSOCIAALTARIEF"] not in (None, "")
                session.add(member)

                product_id = int(row["EAN"])
                product = session.get(EBProduct, product_id)

                if product is None:
                    product = EBProduct(id=product_id)

                product.member_id = id
                product.name = row["PRODUCT"]
                product.ean = int(row["EAN"])
                product.connection_type = EBConnectionType(row["AANSLUITING"])
                product.start_date = dt.datetime.strptime(
                    row["STARTDATUM"], "%d/%m/%Y %H:%M:%S"
                ).date()
                product.end_date = (
                    dt.datetime.strptime(row["EINDDATUM"], "%d/%m/%Y %H:%M:%S").date()
                    if row["EINDDATUM"]
                    else None
                )
                product.grid_operator = GridOperator(row["DISTRIBUTIENET"])
                session.add(product)
            session.commit()
