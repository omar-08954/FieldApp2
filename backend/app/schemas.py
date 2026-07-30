from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


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


class TaskCreate(BaseModel):
    technician_id: int | None = None
    technician_name: str = "غير مسجل"
    task_number: str = Field(min_length=1, max_length=120)
    subscription_number: str = "غير مسجل"
    task_type: str = "تقني"
    task_status: str = "تم الفحص"
    city: str | None = None
    notes: str | None = None
    execution_date: date | None = None


class TaskPublic(TaskCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    needs_review: bool
    created_at: datetime
    updated_at: datetime | None


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=10, max_length=256)
    full_name: str = Field(min_length=2, max_length=200)
    role: str = "technician"
    city: str | None = None


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
    created_at: datetime


class Page(BaseModel):
    items: list[TaskPublic]
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


class ImportResult(BaseModel):
    batch_id: int
    total_rows: int
    imported_rows: int
    review_rows: int


class AssistantMessage(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class AssistantReply(BaseModel):
    answer: str
    available: bool
