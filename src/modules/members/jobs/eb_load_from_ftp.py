import os
from ftplib import FTP

from src.modules.members.jobs.eb_load_from_csv import EBLoadFromCSV

TEMP_FILE_PATH = "temp.csv"


class EBLoadFromFTP:
    def __init__(self, ftp_client: FTP, db_engine, file_path: str):
        self.ftp_client = ftp_client
        self.db_engine = db_engine
        self.file_path = file_path

    def __call__(self):
        self.ftp_client.login()
        self.ftp_client.cwd("/path/to/csv")
        with open(TEMP_FILE_PATH, "wb") as f:
            self.ftp_client.retrbinary(f"RETR {self.file_path}", f.write)
        EBLoadFromCSV(TEMP_FILE_PATH, self.db_engine)()
        self.ftp_client.quit()
        os.remove(TEMP_FILE_PATH)
