import os
import uuid
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./task_router.db")

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class TaskModel(Base):
    __tablename__ = "tasks"

    task_id = Column(
        String,
        primary_key=True,
        index=True,
        default=lambda: f"tsk_{uuid.uuid4().hex[:8]}",
    )
    candidate_id = Column(
        String, index=True, default="priya.sharma@gmail.com", nullable=False
    )
    source_email_id = Column(String, index=True, nullable=False)
    thread_id = Column(String, index=True, nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    assignee_id = Column(String, nullable=False)
    category = Column(String, nullable=False)
    priority = Column(String, default="medium", nullable=False)
    due_date = Column(String, nullable=True)
    deal_value_inr = Column(BigInteger, nullable=True)
    company_name = Column(String, nullable=True)
    confidence = Column(Float, default=0.90, nullable=False)
    update_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class EmailLogModel(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(String, index=True, nullable=False)
    candidate_id = Column(
        String, index=True, default="priya.sharma@gmail.com", nullable=False
    )
    thread_id = Column(String, index=True, nullable=False)
    action_taken = Column(String, nullable=False)  # created, updated, skipped
    skip_reason = Column(String, nullable=True)
    category_detected = Column(String, nullable=True)
    raw_subject = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()