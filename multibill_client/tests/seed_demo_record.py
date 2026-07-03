"""One-off helper: insert a sample 'parsed' record into the running app's DB
so the UI has something to display. Not part of the pull cycle - for demo only.
"""
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from models import init_db, get_session, FileRecord  # noqa: E402
from edi_parser import parse_edi, summarize  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "remote", "invoice1.edi.gpg")

with open(FIXTURE, "r", encoding="utf-8") as f:
    raw_text = f.read()

segments = parse_edi(raw_text, segment_sep="~", element_sep="*")

init_db()
session = get_session()
try:
    now = datetime.utcnow()
    record = FileRecord(
        filename="invoice1.edi.gpg",
        remote_path="/incoming/invoice1.edi.gpg",
        local_raw_path="downloads/invoice1.edi.gpg",
        local_decrypted_path="decrypted/invoice1.edi",
        status="parsed",
        parsed_summary=summarize(segments),
        downloaded_at=now,
        decrypted_at=now,
        parsed_at=now,
    )
    session.add(record)
    session.commit()
    print(f"Inserted record id={record.id}, filename={record.filename}, status={record.status}")
finally:
    session.close()
