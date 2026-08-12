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

def ensure_initial_admin() -> None:
    if not settings.initial_admin_username or not settings.initial_admin_password:
        return
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.username == settings.initial_admin_username))
        if not admin:
            db.add(User(
                username=settings.initial_admin_username,
                password_hash=hash_password(settings.initial_admin_password),
                full_name=settings.initial_admin_name,
                role=Role.ADMIN,
            ))
            db.commit()
            logger.warning("Initial administrator account created; change its password after first login")
            return
        if admin.role != Role.ADMIN:
            admin.role = Role.ADMIN
            db.commit()
            logger.warning("Initial administrator username existed with a non-admin role; role was corrected")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ============================================================
# Application startup / lifespan
# ============================================================

@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("========== FIELDAPP STARTUP ==========")

    if settings.environment != "production":
        Base.metadata.create_all(bind=engine)
        # Alembic owns production migrations.
    ensure_initial_admin()
    yield

    logger.info("========== FIELDAPP SHUTDOWN ==========")


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
