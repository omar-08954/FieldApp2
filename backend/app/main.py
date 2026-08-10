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

    # في بيئة التطوير فقط يتم إنشاء الجداول تلقائيًا.
    # في الإنتاج Alembic هو المسؤول عن migrations.
    if settings.environment != "production":
        Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:

        # ====================================================
        # 1. تحميل المستخدمين الافتراضيين
        # ====================================================

        from app.setup_users_accounts_information import DEFAULT_USERS

        logger.info(
            "Default users loaded: %s",
            len(DEFAULT_USERS),
        )

        # ====================================================
        # 2. إنشاء الأدمن من متغيرات Render فقط
        # ====================================================

        admin_created = 0

        if (
            settings.initial_admin_username
            and settings.initial_admin_password
        ):

            logger.info(
                "Initial admin credentials are configured."
            )

            admin = db.scalar(
                select(User).where(
                    User.username == settings.initial_admin_username
                )
            )

            if admin is None:

                admin = User(
                    username=settings.initial_admin_username,
                    password_hash=hash_password(
                        settings.initial_admin_password
                    ),
                    full_name=settings.initial_admin_name,
                    role=Role.ADMIN,
                    is_active=True,
                )

                db.add(admin)

                admin_created = 1

                logger.info(
                    "Initial administrator account queued for creation."
                )

            else:

                logger.info(
                    "Initial administrator account already exists."
                )

        else:

            logger.warning(
                "Initial admin environment variables are not configured. "
                "No default administrator will be created."
            )

        # ====================================================
        # 3. إنشاء المستخدمين الافتراضيين
        # ====================================================

        technicians_created = 0
        technicians_skipped = 0

        for user_data in DEFAULT_USERS:

            username = str(user_data["username"])

            existing = db.scalar(
                select(User).where(
                    User.username == username
                )
            )

            if existing is not None:

                technicians_skipped += 1
                continue

            user = User(
                username=username,
                password_hash=user_data["password_hash"],
                full_name=user_data["full_name"],
                city=user_data["city"],
                role=Role.TECHNICIAN,
                is_active=user_data.get("is_active", True),
            )

            db.add(user)

            technicians_created += 1

        # ====================================================
        # 4. حفظ جميع المستخدمين في Transaction واحدة
        # ====================================================

        if admin_created or technicians_created:
            db.commit()

        else:
            # لا يوجد شيء جديد للحفظ.
            db.rollback()

        logger.info(
            "Initial administrator accounts created: %s",
            admin_created,
        )

        logger.info(
            "Default technician accounts created: %s",
            technicians_created,
        )

        logger.info(
            "Default technician accounts skipped: %s",
            technicians_skipped,
        )

        # ====================================================
        # 5. العدد النهائي للمستخدمين
        # ====================================================

        total_users = db.scalar(
            select(func.count()).select_from(User)
        )

        logger.info(
            "Total users after startup: %s",
            total_users,
        )

        logger.info(
            "========== FIELDAPP STARTUP COMPLETE =========="
        )

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
