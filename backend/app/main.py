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

settings = get_settings()
log_directory = Path(settings.logs_dir)
log_directory.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s", handlers=[logging.StreamHandler(), RotatingFileHandler(log_directory / "fieldapp-api.log", maxBytes=settings.log_max_bytes, backupCount=settings.log_backup_count, encoding="utf-8")])

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
                db.add(
                    User(
                        username=settings.initial_admin_username,
                        password_hash=hash_password(settings.initial_admin_password),
                        full_name=settings.initial_admin_name,
                        role=Role.ADMIN,
                    )
                )
                db.commit()
                logging.getLogger(__name__).info(
                    "Initial administrator account created"
                )

        # إنشاء الفنيين الافتراضيين
        from app.setup_users_accounts_information import DEFAULT_USERS

        created = 0

        for user_data in DEFAULT_USERS:
            existing = db.scalar(
                select(User).where(
                    User.username == user_data["username"]
                )
            )

            if existing:
                continue

            db.add(
                User(
                    username=user_data["username"],
                    password_hash=user_data["password_hash"],
                    full_name=user_data["full_name"],
                    city=user_data["city"],
                    role=Role.TECHNICIAN,
                    is_active=True,
                )
            )

            created += 1

        if created:
            db.commit()
            logging.getLogger(__name__).info(
                "Created %s default technician accounts",
                created,
            )

    finally:
        db.close()

    yield
app = FastAPI(title="FieldApp Enterprise API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix="/api/v1", tags=["FieldApp"])


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logging.getLogger(__name__).exception("Database request failed", extra={"path": request.url.path})
    return JSONResponse(status_code=500, content={"detail": "تعذر حفظ البيانات حالياً. حاول مرة أخرى."})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger(__name__).exception("Unhandled API request error", extra={"path": request.url.path})
    return JSONResponse(status_code=500, content={"detail": "حدث خطأ غير متوقع وتم تسجيله للمراجعة."})

@app.get("/health")
def health(): return {"status": "ok"}
