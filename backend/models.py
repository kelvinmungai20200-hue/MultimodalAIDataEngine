from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import uuid


class Base(DeclarativeBase):
    pass


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    owner_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Use a different attribute name (dataset_metadata) to avoid clashing with SQLAlchemy's Base.metadata
    dataset_metadata: Mapped[Optional[dict]] = mapped_column('metadata', JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assets = relationship("Asset", back_populates="dataset", cascade="all, delete-orphan")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=True)
    s3_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    filename: Mapped[Optional[str]] = mapped_column(String(512))
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128))
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    sha256: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="pending")
    annotations: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dataset = relationship("Dataset", back_populates="assets")
    annotation_rows = relationship("Annotation", back_populates="asset", cascade="all, delete-orphan")
    embeddings = relationship("EmbeddingRef", back_populates="asset", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_assets_dataset_status", "dataset_id", "status"),
    )


class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    annotator_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    annotation: Mapped[dict] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    asset = relationship("Asset", back_populates="annotation_rows")

    __table_args__ = (
        Index("ix_annotations_asset_status", "asset_id", "status"),
    )


class LLMRecord(Base):
    __tablename__ = "llm_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text)
    responses: Mapped[Optional[dict]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="pending")
    rlhf_feedback: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    embeddings = relationship("EmbeddingRef", back_populates="llm_record", cascade="all, delete-orphan")


class EmbeddingRef(Base):
    __tablename__ = "embeddings_refs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=True)
    llm_record_id: Mapped[Optional[int]] = mapped_column(ForeignKey("llm_records.id", ondelete="CASCADE"), nullable=True)
    vector_db_id: Mapped[str] = mapped_column(String(255), nullable=False)
    model_name: Mapped[Optional[str]] = mapped_column(String(255))
    dimension: Mapped[Optional[int]] = mapped_column(Integer)
    normalized: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    asset = relationship("Asset", back_populates="embeddings")
    llm_record = relationship("LLMRecord", back_populates="embeddings")

    __table_args__ = (
        Index("ix_embeddings_vector_db_id", "vector_db_id"),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, server_default="annotator")
    api_key_hash: Mapped[Optional[str]] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(255))
    target_id: Mapped[Optional[int]] = mapped_column(Integer)
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hashed_key: Mapped[str] = mapped_column(String(512), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class TaskQueue(Base):
    __tablename__ = "task_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_type: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="queued")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error: Mapped[Optional[str]] = mapped_column(Text)
    result: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class ReconcileJob(Base):
    __tablename__ = "reconcile_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="pending")
    total_refs: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    processed_refs: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    upserted: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    skipped: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    config: Mapped[Optional[dict]] = mapped_column(JSON)
    errors: Mapped[Optional[dict]] = mapped_column(JSON)
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_reconcile_jobs_status", "status"),
    )


# Convenience helper for quick local testing (not used by Alembic migrations)
def create_all_tables(engine):
    """Create all tables using the SQLAlchemy models. For local testing only.

    Alembic should be used in production for managed migrations.
    """
    Base.metadata.create_all(engine)
