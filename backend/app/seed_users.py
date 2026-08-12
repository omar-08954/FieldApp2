import logging

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.core.config import get_settings
from app.models import User, Role
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
    admin_updated = 0
    technicians_created = 0
    technicians_updated = 0

    try:
        # =====================================================
        # 1. إنشاء الأدمن من Render Environment Variables
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
                admin.password_hash = hash_password(
                    settings.initial_admin_password
                )
                admin.full_name = settings.initial_admin_name
                admin.role = Role.ADMIN
                admin.is_active = True
                admin_updated = 1

                logger.info(
                    "Initial administrator reset and updated: %s",
                    settings.initial_admin_username,
                )

        else:
            logger.warning(
                "INITIAL_ADMIN_USERNAME or INITIAL_ADMIN_PASSWORD "
                "is missing. Administrator was not created."
            )

        # =====================================================
        # 2. إنشاء الفنيين الافتراضيين
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
                existing.password_hash = user_data["password_hash"]
                existing.full_name = user_data["full_name"]
                existing.city = user_data["city"]
                existing.role = Role.TECHNICIAN
                existing.is_active = user_data.get("is_active", True)
                technicians_updated += 1
                continue

            db.add(
                User(
                    username=username,
                    password_hash=user_data["password_hash"],
                    full_name=user_data["full_name"],
                    city=user_data["city"],
                    role=Role.TECHNICIAN,
                    is_active=user_data.get("is_active", True),
                )
            )

            technicians_created += 1

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
            "Admin updated: %d",
            admin_updated,
        )

        logger.info(
            "Technicians created: %d",
            technicians_created,
        )

        logger.info(
            "Technicians updated: %d",
            technicians_updated,
        )

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
