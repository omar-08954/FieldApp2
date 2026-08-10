import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import router
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import Role, User


settings = get_settings()


# ============================================================
# Logging
# ============================================================

log_directory = Path(settings.logs_dir)
log_directory.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            log_directory / "fieldapp-api.log",
            maxBytes=settings.log_max_bytes,
            backupCount=settings.log_backup_count,
            encoding="utf-8",
        ),
    ],
)

logger = logging.getLogger(__name__)


# ============================================================
# Application startup / lifespan
# ============================================================

@asynccontextmanager
async def lifespan(_: FastAPI):

    logger.info("========== FIELDAPP STARTUP ==========")

    # إنشاء الجداول في بيئة التطوير فقط.
    # في الإنتاج Alembic هو المسؤول عن migrations.
    if settings.environment != "production":
        Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:

        # ====================================================
        # 1. إنشاء حساب الأدمن من متغيرات Render
        # ====================================================

        logger.info(
            "Initial admin username configured: %s",
            bool(settings.initial_admin_username),
        )

        logger.info(
            "Initial admin password configured: %s",
            bool(settings.initial_admin_password),
        )

        if (
            settings.initial_admin_username
            and settings.initial_admin_password
        ):

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

                logger.info(
                    "Initial administrator account created successfully."
                )

            else:

                logger.info(
                    "Initial administrator account already exists."
                )

        else:

            logger.warning(
                "Initial admin environment variables are not configured."
            )

        # ====================================================
        # 2. إنشاء المستخدمين الافتراضيين
        # ====================================================

        from app.setup_users_accounts_information import DEFAULT_USERS

        logger.info(
            "Default users loaded from setup_users_accounts_information.py: %s",
            len(DEFAULT_USERS),
        )

        created = 0
        skipped = 0

        for user_data in DEFAULT_USERS:

            existing = db.scalar(
                select(User).where(
                    User.username == user_data["username"]
                )
            )

            if existing:

                skipped += 1
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

        logger.info(
            "Default technician accounts created: %s",
            created,
        )

        logger.info(
            "Default technician accounts skipped because they already exist: %s",
            skipped,
        )

        # ====================================================
        # 3. إظهار العدد النهائي للمستخدمين في الـ Logs
        # ====================================================

        total_users = db.scalar(
    select(func.count()).select_from(User)
        )

        logger.info(
            "Total users after startup: %s",
            total_users,
        )

        logger.info("========== FIELDAPP STARTUP COMPLETE ==========")

    except Exception:

        db.rollback()

        logger.exception(
            "FAILED TO INITIALIZE USERS DURING APPLICATION STARTUP"
        )

        raise

    finally:

        db.close()

    yield


# ============================================================
# FastAPI application
# ============================================================

app = FastAPI(
    title="FieldApp Enterprise API",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# API routes
# ============================================================

app.include_router(
    router,
    prefix="/api/v1",
    tags=["FieldApp"],
)


# ============================================================
# Database exception handler
# ============================================================

@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(
    request: Request,
    exc: SQLAlchemyError,
) -> JSONResponse:

    logger.exception(
        "Database request failed",
        extra={
            "path": request.url.path,
        },
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "تعذر حفظ البيانات حالياً. حاول مرة أخرى."
        },
    )


# ============================================================
# General exception handler
# ============================================================

@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:

    logger.exception(
        "Unhandled API request error",
        extra={
            "path": request.url.path,
        },
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "حدث خطأ غير متوقع وتم تسجيله للمراجعة."
        },
    )


# ============================================================
# Health check
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "ok"
    }
