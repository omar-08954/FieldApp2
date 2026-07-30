import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from app.api.routes import router
from app.core.config import get_settings
from app.core.database import Base, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s", handlers=[logging.StreamHandler(), logging.FileHandler("fieldapp-api.log", encoding="utf-8")])
settings = get_settings()

@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.environment != "production":
        Base.metadata.create_all(bind=engine)  # Alembic owns production migrations.
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
