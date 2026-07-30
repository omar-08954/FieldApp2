from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Notification, User


def notify_roles(db: Session, roles: tuple[str, ...], event_type: str, title: str, message: str) -> None:
    users = db.scalars(select(User).where(User.role.in_(roles), User.is_active.is_(True))).all()
    db.add_all([Notification(user_id=user.id, event_type=event_type, title=title, message=message) for user in users])
