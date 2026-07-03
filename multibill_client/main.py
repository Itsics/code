"""FastAPI + Scheduler שמריץ את מחזור המשיכה: SFTP -> פענוח PGP -> פירוק EDI -> DB.

TODO: אין כרגע Authentication/Authorization ל-API - הוא פתוח לחלוטין.
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import config, save_config
from models import init_db, get_session, FileRecord
from sftp_client import SFTPClient
from decryption import decrypt_file
from edi_parser import parse_edi, summarize

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("multibill")

scheduler = BackgroundScheduler()


def run_pull_cycle():
    """מחזור משיכה מלא: מתחבר ל-SFTP, מוריד קבצים חדשים בלבד, מפענח ומפרק."""
    session = get_session()
    try:
        with SFTPClient() as sftp:
            remote_files = sftp.list_remote_files()
            existing = {r.filename for r in session.query(FileRecord).all()}
            new_files = [f for f in remote_files if f not in existing]

            for filename in new_files:
                record = FileRecord(filename=filename, remote_path=f"{sftp.remote_dir}/{filename}")
                session.add(record)
                session.commit()

                try:
                    local_raw = sftp.download_file(filename)
                    record.local_raw_path = local_raw
                    record.status = "downloaded"
                    record.downloaded_at = datetime.utcnow()
                    session.commit()

                    decrypted_path = decrypt_file(local_raw)
                    record.local_decrypted_path = decrypted_path
                    record.status = "decrypted"
                    record.decrypted_at = datetime.utcnow()
                    session.commit()

                    with open(decrypted_path, "r", encoding="utf-8", errors="replace") as f:
                        raw_text = f.read()
                    segments = parse_edi(
                        raw_text,
                        segment_sep=config["edi"]["segment_separator"],
                        element_sep=config["edi"]["element_separator"],
                    )
                    record.parsed_summary = summarize(segments)
                    record.status = "parsed"
                    record.parsed_at = datetime.utcnow()
                    session.commit()

                except Exception as exc:  # noqa: BLE001
                    logger.exception("Failed processing %s", filename)
                    record.status = "error"
                    record.error_message = str(exc)
                    session.commit()
    except Exception:
        logger.exception("Pull cycle failed")
    finally:
        session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    interval = config["scheduler"]["interval_minutes"]
    scheduler.add_job(run_pull_cycle, "interval", minutes=interval, id="pull_cycle")
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Multibill Client", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/api/files")
def list_files():
    session = get_session()
    try:
        records = session.query(FileRecord).order_by(FileRecord.created_at.desc()).all()
        return [
            {
                "id": r.id,
                "filename": r.filename,
                "status": r.status,
                "parsed_summary": r.parsed_summary,
                "error_message": r.error_message,
                "downloaded_at": r.downloaded_at,
                "decrypted_at": r.decrypted_at,
                "parsed_at": r.parsed_at,
            }
            for r in records
        ]
    finally:
        session.close()


@app.get("/api/files/{file_id}")
def get_file(file_id: int):
    session = get_session()
    try:
        record = session.get(FileRecord, file_id)
        if not record:
            raise HTTPException(status_code=404, detail="File not found")
        return {
            "id": record.id,
            "filename": record.filename,
            "remote_path": record.remote_path,
            "status": record.status,
            "parsed_summary": record.parsed_summary,
            "error_message": record.error_message,
        }
    finally:
        session.close()


@app.post("/api/run-cycle")
def trigger_pull_cycle():
    run_pull_cycle()
    return {"status": "ok"}


PASSWORD_PLACEHOLDER = "********"


class SFTPSettings(BaseModel):
    host: str
    port: int = 22
    username: str
    password: str = ""
    private_key_path: str = ""
    remote_dir: str = "/"
    local_dir: str = "./downloads"


class EDISettings(BaseModel):
    segment_separator: str = "~"
    element_separator: str = "*"


class ConfigUpdate(BaseModel):
    sftp: SFTPSettings
    edi: EDISettings


@app.get("/api/config")
def get_settings():
    sftp_cfg = dict(config.get("sftp", {}))
    sftp_cfg["password"] = PASSWORD_PLACEHOLDER if sftp_cfg.get("password") else ""
    return {"sftp": sftp_cfg, "edi": config.get("edi", {})}


@app.post("/api/config")
def update_settings(update: ConfigUpdate):
    sftp_values = update.sftp.model_dump()
    if sftp_values["password"] == PASSWORD_PLACEHOLDER:
        sftp_values["password"] = config.get("sftp", {}).get("password", "")

    save_config({"sftp": sftp_values, "edi": update.edi.model_dump()})
    return {"status": "ok"}
