from typing import Generic, TypeVar
from sqlalchemy import Select, and_, func, or_, select
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
    def list(self, page: int, page_size: int, search: str | None = None, status: str | None = None, search_field: str = "all") -> tuple[list[Task], int]:
        statement: Select = select(Task)
        if search:
            terms = [part for part in search.strip().split() if part]
            field_map = {
                "city": Task.city,
                "technician": Task.technician_name,
                "technician_name": Task.technician_name,
                "task": Task.task_number,
                "task_number": Task.task_number,
                "status": Task.task_status,
                "task_status": Task.task_status,
                "task_type": Task.task_type,
                "subscription_number": Task.subscription_number,
            }
            if search_field in field_map:
                column = field_map[search_field]
                statement = statement.where(and_(*[column.ilike(f"%{term}%") for term in terms]))
            else:
                technician_match = and_(*[Task.technician_name.ilike(f"%{term}%") for term in terms])
                other_matches = or_(*[
                    column.ilike(f"%{term}%")
                    for term in terms
                    for column in (Task.task_number, Task.subscription_number, Task.city, Task.task_status, Task.task_type)
                ])
                statement = statement.where(or_(technician_match, other_matches))
        if status: statement = statement.where(Task.task_status == status)
        total = self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0
        return list(self.db.scalars(statement.order_by(Task.created_at.desc()).offset((page - 1) * page_size).limit(page_size))), total
