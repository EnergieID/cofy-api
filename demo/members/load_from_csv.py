import csv
import logging
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from cofy.modules.members import Address, ConnectionType, Contract, CustomerType, Member, NamedIdentifier

LOGGER = logging.getLogger(__name__)

CSV_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class CSVColumns(StrEnum):
    EAN = "ean"
    MEMBER_ID = "member_id"
    ACTIVATION_CODE = "activation_code"
    ADDRESS_ID = "address_id"
    CUSTOMER_TYPE = "customer_type"
    CONNECTION_TYPE = "connection_type"
    PROVIDER_ID = "provider_id"
    PROVIDER_NAME = "provider_name"
    PRODUCT_ID = "product_id"
    PRODUCT_NAME = "product_name"
    DISTRIBUTOR_ID = "distributor_id"
    DISTRIBUTOR_NAME = "distributor_name"
    START_DATE = "start_date"
    END_DATE = "end_date"
    LAST_INVOICE_DATE = "last_invoice_date"
    IS_GREEN = "is_green"


def example_load_members_from_file(file_path: Path) -> dict[str, Member]:
    members: dict[str, Member] = {}
    contracts_by_member_and_address: dict[str, dict[str, list[Contract]]] = {}

    with file_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)

        for row_number, row in enumerate(reader, start=2):
            try:
                member_id = row[CSVColumns.MEMBER_ID]
                if member_id not in members:
                    members[member_id] = Member(
                        id=member_id,
                        activation_code=row[CSVColumns.ACTIVATION_CODE] or None,
                    )
                    contracts_by_member_and_address[member_id] = {}

                contract = Contract(
                    ean=row[CSVColumns.EAN],
                    customer_type=CustomerType(row[CSVColumns.CUSTOMER_TYPE]),
                    connection_type=ConnectionType(row[CSVColumns.CONNECTION_TYPE]),
                    providor=NamedIdentifier(
                        id=row[CSVColumns.PROVIDER_ID],
                        name=row[CSVColumns.PROVIDER_NAME],
                    ),
                    product=NamedIdentifier(
                        id=row[CSVColumns.PRODUCT_ID],
                        name=row[CSVColumns.PRODUCT_NAME],
                    ),
                    distributor=NamedIdentifier(
                        id=row[CSVColumns.DISTRIBUTOR_ID],
                        name=row[CSVColumns.DISTRIBUTOR_NAME],
                    ),
                    start_date=datetime.strptime(row[CSVColumns.START_DATE], CSV_DATETIME_FORMAT),
                    end_date=datetime.strptime(row[CSVColumns.END_DATE], CSV_DATETIME_FORMAT)
                    if row[CSVColumns.END_DATE]
                    else None,
                    last_invoice_date=datetime.strptime(row[CSVColumns.LAST_INVOICE_DATE], CSV_DATETIME_FORMAT)
                    if row[CSVColumns.LAST_INVOICE_DATE]
                    else None,
                    is_green=row[CSVColumns.IS_GREEN].strip().lower() == "true",
                )

                address_id = row[CSVColumns.ADDRESS_ID]
                contracts_by_member_and_address[member_id].setdefault(address_id, []).append(contract)
            except ValueError as exc:
                LOGGER.warning("Skipping invalid member row %s in %s: %s", row_number, file_path, exc)
                continue

    for member_id, member in members.items():
        member.addresses = [
            Address(contracts=contracts) for _, contracts in contracts_by_member_and_address[member_id].items()
        ]

    return members
