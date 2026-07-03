"""טבלת מעקב קבצים - מייצגת כל קובץ שנמשך מה-SFTP ואת מצבו במחזור העיבוד."""
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

from config import config

Base = declarative_base()


class FileRecord(Base):
    __tablename__ = "file_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, unique=True, nullable=False)
    remote_path = Column(String, nullable=False)
    local_raw_path = Column(String, nullable=True)
    local_decrypted_path = Column(String, nullable=True)

    # pending -> downloaded -> decrypted -> parsed  (או error בכל שלב)
    status = Column(String, default="pending", nullable=False)
    error_message = Column(Text, nullable=True)

    parsed_summary = Column(Text, nullable=True)

    downloaded_at = Column(DateTime, nullable=True)
    decrypted_at = Column(DateTime, nullable=True)
    parsed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


engine = create_engine(
    config["database"]["url"],
    connect_args={"check_same_thread": False} if config["database"]["url"].startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
