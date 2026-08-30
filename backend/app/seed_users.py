import logging

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.core.config import get_settings
from app.models import Task, TechnicianAlias, User, Role
from app.services.importer import _normalized, match_technician
from app.setup_users_accounts_information import DEFAULT_USERS


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger("fieldapp.seed_users")

settings = get_settings()


def seed_users() -> None:
    db = SessionLocal()

    admin_created = 0
    technicians_created = 0
    technicians_existing = 0

    try:
        # =====================================================
        # 1. إنشاء المدير الأولي من متغيرات البيئة مرة واحدة فقط.
        # =====================================================

        if (
            settings.initial_admin_username
            and settings.initial_admin_password
        ):
            admin = db.scalar(
                select(User).where(
                    User.username == settings.initial_admin_username
                )
            )

            if admin is None:
                db.add(
                    User(
                        username=settings.initial_admin_username,
                        password_hash=hash_password(
                            settings.initial_admin_password
                        ),
                        full_name=settings.initial_admin_name,
                        role=Role.ADMIN,
                        is_active=True,
                    )
                )

                admin_created = 1

                logger.info(
                    "Created initial administrator: %s",
                    settings.initial_admin_username,
                )
            else:
                logger.info("Initial administrator already exists: %s", settings.initial_admin_username)

        else:
            logger.warning(
                "INITIAL_ADMIN_USERNAME or INITIAL_ADMIN_PASSWORD "
                "is missing. Administrator was not created."
            )

        # =====================================================
        # 2. إنشاء الفنيين الافتراضيين مرة واحدة؛ لا نعيد تفعيل أو نغير
        # كلمات مرور الحسابات التي عدّلها المدير لاحقاً.
        # =====================================================

        logger.info(
            "Loading %d default technician accounts.",
            len(DEFAULT_USERS),
        )

        for user_data in DEFAULT_USERS:

            username = str(user_data["username"])

            existing = db.scalar(
                select(User).where(
                    User.username == username
                )
            )

            if existing is not None:
                technicians_existing += 1
                continue

            db.add(
                User(
                    username=username,
                    password_hash=user_data.get("password_hash") or hash_password(settings.default_technician_password),
                    full_name=user_data["full_name"],
                    city=user_data["city"],
                    role=Role.TECHNICIAN,
                    is_active=user_data.get("is_active", True),
                )
            )

            technicians_created += 1

        # Repair ownership/city for tasks imported before technician matching was added.
        technicians = list(db.scalars(select(User).where(User.is_active.is_(True))).all())
        aliases = {_normalized(alias.alias_name): alias.technician_id for alias in db.scalars(select(TechnicianAlias)).all()}
        tasks_repaired = 0
        for task in db.scalars(select(Task).where(Task.technician_name != "غير مسجل")).all():
            technician = match_technician(task.technician_name, technicians, aliases)
            if technician and (task.technician_id != technician.id or not task.city):
                task.technician_id = technician.id
                task.technician_name = technician.full_name
                if not task.city:
                    task.city = technician.city
                tasks_repaired += 1

        # =====================================================
        # 3. Commit واحد لكل المستخدمين
        # =====================================================

        db.commit()

        logger.info(
            "Users seed completed successfully."
        )

        logger.info(
            "Admin created: %d",
            admin_created,
        )

        logger.info(
            "Technicians created: %d",
            technicians_created,
        )

        logger.info(
            "Technicians already present: %d",
            technicians_existing,
        )
        logger.info("Existing tasks repaired with technician/city data: %d", tasks_repaired)

    except Exception:
        db.rollback()

        logger.exception(
            "USER SEED FAILED"
        )

        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_users()
