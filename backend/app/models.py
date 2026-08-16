from datetime import date, datetime
from enum import StrEnum
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Role(StrEnum):
    ADMIN = "admin"
    TECHNICIAN = "technician"


class TaskStatus(StrEnum):
    BLOCKED = "عائق"
    INSPECTED = "تم الفحص"
    REMOVED = "مزال"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200), index=True)
    role: Mapped[str] = mapped_column(String(30), default=Role.TECHNICIAN)
    city: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    technician_name: Mapped[str] = mapped_column(String(200), default="غير مسجل")
    task_number: Mapped[str] = mapped_column(String(120), index=True)
    subscription_number: Mapped[str] = mapped_column(String(120), default="غير مسجل", index=True)
    task_type: Mapped[str] = mapped_column(String(80), default="تقني")
    task_status: Mapped[str] = mapped_column(String(80), default=TaskStatus.INSPECTED)
    city: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    execution_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AssignedTask(Base):
    __tablename__ = "assigned_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    task_number: Mapped[str] = mapped_column(String(120), index=True)
    subscription_number: Mapped[str] = mapped_column(String(120), default="غير مسجل")
    task_type: Mapped[str] = mapped_column(String(80), default="تقني")
    task_status: Mapped[str] = mapped_column(String(80), default="عائق")
    city: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    assigned_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assigned_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Material(Base):
    __tablename__ = "materials"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    unit: Mapped[str] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DailyReport(Base):
    __tablename__ = "daily_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    technician_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    report_date: Mapped[date] = mapped_column(Date, index=True)
    image_key: Mapped[str] = mapped_column(String(500))
    image_mime: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    imported_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, default=0)
    review_rows: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImportReview(Base):
    __tablename__ = "import_reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"), index=True)
    source_row: Mapped[int] = mapped_column(Integer)
    task_number: Mapped[str | None] = mapped_column(String(120))
    technician_name: Mapped[str | None] = mapped_column(String(200))
    subscription_number: Mapped[str | None] = mapped_column(String(120))
    task_type: Mapped[str | None] = mapped_column(String(80))
    exception_type: Mapped[str] = mapped_column(String(100))
    error_message: Mapped[str] = mapped_column(Text)
    postgres_message: Mapped[str | None] = mapped_column(Text)
    action_taken: Mapped[str] = mapped_column(String(120))
    raw_payload: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
