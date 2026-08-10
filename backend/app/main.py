import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import router
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import Role, User

@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.environment != "production":
        Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # إنشاء الأدمن من متغيرات Render
        if settings.initial_admin_username and settings.initial_admin_password:
            admin = db.scalar(
                select(User).where(
                    User.username == settings.initial_admin_username
                )
            )

            if not admin:
                admin = User(
                    username=settings.initial_admin_username,
                    password_hash=hash_password(
                        settings.initial_admin_password
                    ),
                    full_name=settings.initial_admin_name,
                    role=Role.ADMIN,
                )

                db.add(admin)
                db.commit()

                logging.info(
                    "Initial administrator account created"
                )

        # استيراد قائمة المستخدمين الافتراضيين
        from app.setup_users_accounts_information import DEFAULT_USERS

        created = 0

        # إنشاء المستخدمين الـ 37
        for user_data in DEFAULT_USERS:

            existing = db.scalar(
                select(User).where(
                    User.username == user_data["username"]
                )
            )

            if existing:
                continue

            user = User(
                username=user_data["username"],
                password_hash=user_data["password_hash"],
                full_name=user_data["full_name"],
                city=user_data["city"],
                role=Role.TECHNICIAN,
                is_active=user_data.get("is_active", True),
            )

            db.add(user)
            created += 1

        if created:
            db.commit()

        logging.info(
            "Default users created: %s",
            created
        )

    except Exception:
        db.rollback()
        logging.exception(
            "Failed to initialize default users"
        )
        raise

    finally:
        db.close()

    yield
