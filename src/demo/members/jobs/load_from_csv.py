import csv

from sqlalchemy.orm import Session

from src.modules.members.models.db_member import DBMember


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

                member = session.get(DBMember, member_id)
                if member is None:
                    member = DBMember(
                        id=member_id,
                        email=email,
                        activation_code=activation_code,
                    )
                else:
                    member.email = email
                    member.activation_code = activation_code
                session.add(member)
            session.commit()
