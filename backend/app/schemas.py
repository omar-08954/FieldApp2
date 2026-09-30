from datetime import date, datetime
from typing import Generic, Literal, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str
    role: str
    city: str | None


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=256)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=8, max_length=256)
    new_password: str = Field(min_length=10, max_length=256)


class TaskCreate(BaseModel):
    technician_id: int | None = None
    technician_name: str = "غير مسجل"
    task_number: str = Field(min_length=1, max_length=120)
    subscription_number: str = "غير مسجل"
    task_type: str = "تقني"
    task_status: str = "تم الفحص"
    city: str | None = None
    notes: str | None = None
    customer_name: str | None = Field(default=None, max_length=200)
    customer_phone: str | None = Field(default=None, max_length=40)
    customer_signature: str | None = None
    customer_rating: int | None = Field(default=None, ge=1, le=5)
    customer_feedback: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    due_at: datetime | None = None
    execution_date: date | None = None


class TaskPublic(TaskCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    needs_review: bool
    created_at: datetime
    updated_at: datetime | None


class TaskUpdate(BaseModel):
    technician_id: int | None = None
    technician_name: str | None = Field(default=None, max_length=200)
    subscription_number: str | None = Field(default=None, max_length=120)
    task_type: str | None = Field(default=None, max_length=80)
    task_status: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    customer_name: str | None = Field(default=None, max_length=200)
    customer_phone: str | None = Field(default=None, max_length=40)
    customer_signature: str | None = None
    customer_rating: int | None = Field(default=None, ge=1, le=5)
    customer_feedback: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    due_at: datetime | None = None
    execution_date: date | None = None


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=10, max_length=256)
    full_name: str = Field(min_length=2, max_length=200)
    role: str = "technician"
    city: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    role: str | None = None
    city: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None


class MaterialCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    quantity: int = Field(ge=0)
    unit: str = Field(min_length=1, max_length=40)
    notes: str | None = None


class MaterialPublic(MaterialCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime | None


class MaterialMovementPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    material_id: int
    actor_id: int | None
    quantity_delta: int
    quantity_before: int
    quantity_after: int
    reason: str | None
    created_at: datetime


class TaskMaterialUsageCreate(BaseModel):
    material_id: int
    quantity: int = Field(gt=0)


class TaskMaterialUsagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: int
    material_id: int
    quantity: int
    actor_id: int | None
    created_at: datetime


class AssignmentCreate(BaseModel):
    technician_id: int
    task_number: str = Field(min_length=1, max_length=120)
    subscription_number: str = "غير مسجل"
    task_type: str = "تقني"
    task_status: str = "عائق"
    city: str | None = None
    notes: str | None = None
    assigned_date: date | None = None


class AssignmentPublic(AssignmentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    completed_at: datetime | None
    completion_latitude: float | None
    completion_longitude: float | None
    created_at: datetime


class AssignmentComplete(BaseModel):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class CustomerFeedback(BaseModel):
    signature: str | None = None
    rating: int = Field(ge=1, le=5)
    feedback: str | None = Field(default=None, max_length=2000)


class PublicCustomerFeedback(CustomerFeedback):
    task_number: str = Field(min_length=1, max_length=120)
    customer_phone: str = Field(min_length=3, max_length=40)


class TechnicianSuggestion(BaseModel):
    technician_id: int
    technician_name: str
    city: str | None
    active_assignments: int
    score: float


class OperationsAnalytics(BaseModel):
    total_tasks: int
    completed_tasks: int
    overdue_tasks: int
    average_rating: float | None
    technician_load: list[dict]


class DailyReportPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    technician_id: int
    technician_name: str
    report_date: date
    image_mime: str
    created_at: datetime


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class DashboardSummary(BaseModel):
    total_tasks: int
    completion_rate: float
    delayed_tasks: int
    needs_review: int
    by_status: list[dict]
    daily_trend: list[dict]
    latest_tasks: list[TaskPublic]
    top_technicians: list[dict]


class TaskReportSummary(BaseModel):
    city: str
    total_tasks: int
    completed_tasks: int
    blocked_tasks: int
    completion_rate: float
    by_status: list[dict]
    latest_tasks: list[TaskPublic]


class DeveloperStatus(BaseModel):
    environment: str
    total_users: int
    total_tasks: int
    pending_import_reviews: int
    unread_notifications: int
    ai_enabled: bool


class CleanupRequest(BaseModel):
    scope: Literal["tasks", "import_reviews"]


class ImportResult(BaseModel):
    batch_id: int
    total_rows: int
    imported_rows: int
    review_rows: int
    skipped_rows: int


class ImportReviewPublic(BaseModel):
    """Safe, operator-facing representation of a quarantined import row."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    batch_id: int | None
    source_row: int
    task_number: str | None
    technician_name: str | None
    subscription_number: str | None
    task_type: str | None
    task_status: str | None
    city: str | None
    notes: str | None
    execution_date: date | None
    field_name: str | None
    suggested_action: str | None
    exception_type: str
    error_message: str
    postgres_message: str | None
    action_taken: str
    status: str
    created_at: datetime


class ImportReviewRepair(BaseModel):
    """The normalized fields an operator may correct before retrying a row."""

    technician_name: str | None = Field(default=None, max_length=200)
    task_number: str | None = Field(default=None, max_length=120)
    subscription_number: str | None = Field(default=None, max_length=120)
    task_type: str | None = Field(default=None, max_length=80)
    task_status: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    execution_date: date | None = None


class ImportBulkTechnicianRepair(BaseModel):
    source_name: str = Field(min_length=1, max_length=200)
    target_name: str = Field(min_length=1, max_length=200)
    reinsert: bool = True


class NotificationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime


class NotificationPage(Page[NotificationPublic]):
    unread_count: int


class MessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    technician_id: int
    sender_id: int | None
    sender_name: str
    body: str
    message_type: str
    report_date: date | None
    created_at: datetime


class MessageCreate(BaseModel):
    technician_id: int | None = None
    body: str = Field(min_length=1, max_length=4000)


class AssistantMessage(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class AssistantReply(BaseModel):
    answer: str
    available: bool
