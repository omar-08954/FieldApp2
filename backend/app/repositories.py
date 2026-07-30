from typing import Generic, TypeVar
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session
from app.models import Task, User

T = TypeVar("T")


class Repository(Generic[T]):
    def __init__(self, db: Session, model: type[T]): self.db, self.model = db, model
    def get(self, entity_id: int) -> T | None: return self.db.get(self.model, entity_id)
    def add(self, entity: T) -> T: self.db.add(entity); return entity


class UserRepository(Repository[User]):
    def __init__(self, db: Session): super().__init__(db, User)
    def by_username(self, username: str) -> User | None:
        return self.db.scalar(select(User).where(User.username == username))


class TaskRepository(Repository[Task]):
    def __init__(self, db: Session): super().__init__(db, Task)
    def list(self, page: int, page_size: int, search: str | None = None, status: str | None = None) -> tuple[list[Task], int]:
        statement: Select = select(Task)
        if search:
            value = f"%{search.strip()}%"
            statement = statement.where(Task.task_number.ilike(value) | Task.subscription_number.ilike(value) | Task.technician_name.ilike(value))
        if status: statement = statement.where(Task.task_status == status)
        total = self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0
        return list(self.db.scalars(statement.order_by(Task.created_at.desc()).offset((page - 1) * page_size).limit(page_size))), total
