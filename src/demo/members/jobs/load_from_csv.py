import csv
import datetime as dt

from sqlalchemy.orm import Session

from src.demo.members.models import DemoMember, DemoProduct


class LoadMembersFromCSV:
    def __init__(self, file_path: str, db_engine):
        self.file_path = file_path
        self.db_engine = db_engine

    def __call__(self):
        with open(self.file_path) as f, Session(self.db_engine) as session:
            reader = csv.DictReader(f)
            for row in reader:
                member_id = row["KLANTNUMMER"]
                email = row["EMAIL"]
                activation_code = row["ACTIVATIECODE"]

                member = session.get(DemoMember, member_id)
                if member is None:
                    member = DemoMember(
                        id=member_id,
                        email=email,
                        activation_code=activation_code,
                    )
                else:
                    member.email = email
                    member.activation_code = activation_code
                session.add(member)

                product_id = int(row["EAN"])
                start_date = dt.datetime.strptime(
                    row["STARTDATUM"], "%d/%m/%Y %H:%M:%S"
                ).date()
                end_date = (
                    dt.datetime.strptime(row["EINDDATUM"], "%d/%m/%Y %H:%M:%S").date()
                    if row["EINDDATUM"]
                    else None
                )

                product = session.get(DemoProduct, product_id)
                if product is None:
                    product = DemoProduct(
                        id=product_id,
                        member_id=member_id,
                        name=row["PRODUCT"],
                        ean=product_id,
                        start_date=start_date,
                        end_date=end_date,
                    )
                else:
                    product.member_id = member_id
                    product.name = row["PRODUCT"]
                    product.ean = product_id
                    product.start_date = start_date
                    product.end_date = end_date
                session.add(product)

            session.commit()
