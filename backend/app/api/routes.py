from datetime import timedelta
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, WebSocket
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from app.api.deps import CurrentUser, Db, current_user, require_roles
from app.core.config import get_settings
from app.core.security import create_token, decode_token, verify_password
from app.models import AssignedTask, DailyReport, ImportReview, Material, Notification, Role, Task, User
from app.repositories import TaskRepository, UserRepository
from app.schemas import AssignmentCreate, AssignmentPublic, AssistantMessage, AssistantReply, DashboardSummary, ImportResult, LoginRequest, MaterialCreate, MaterialPublic, Page, RefreshRequest, TaskCreate, TaskPublic, TokenPair, UserCreate, UserPublic
from app.services.assistant import ask
from app.services.notifications import notify_roles
from app.services.report_storage import report_path, save_report_image
from app.services.events import broker
from app.services.importer import import_workbook

router = APIRouter()
settings = get_settings()


def pair(user: User) -> TokenPair:
    return TokenPair(access_token=create_token(user.username, "access", timedelta(minutes=settings.access_token_expire_minutes)), refresh_token=create_token(user.username, "refresh", timedelta(days=settings.refresh_token_expire_days)), user=user)


@router.post("/auth/login", response_model=TokenPair)
def login(data: LoginRequest, db: Db):
    user = UserRepository(db).by_username(data.username)
    if not user or not user.is_active or not verify_password(data.password, user.password_hash): raise HTTPException(401, "اسم المستخدم أو كلمة المرور غير صحيحين")
    return pair(user)


@router.post("/auth/refresh", response_model=TokenPair)
def refresh(data: RefreshRequest, db: Db):
    try: username = decode_token(data.refresh_token, "refresh")["sub"]
    except Exception: raise HTTPException(401, "انتهت صلاحية الجلسة")
    user = UserRepository(db).by_username(username)
    if not user or not user.is_active: raise HTTPException(401, "انتهت صلاحية الجلسة")
    return pair(user)


@router.get("/auth/me", response_model=UserPublic)
def me(user: CurrentUser): return user


@router.get("/tasks", response_model=Page)
def tasks(db: Db, _: CurrentUser, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), search: str | None = None, status: str | None = None):
    items, total = TaskRepository(db).list(page, page_size, search, status)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("/tasks", response_model=TaskPublic, status_code=201)
async def create_task(payload: TaskCreate, db: Db, user: CurrentUser):
    task = Task(**payload.model_dump(exclude_none=True)); db.add(task); db.commit(); db.refresh(task)
    notify_roles(db, (Role.ADMIN, Role.MANAGER), "task_created", "مهمة جديدة", f"تمت إضافة المهمة {task.task_number}"); db.commit()
    await broker.publish("task.created", {"id": task.id, "actor": user.full_name})
    return task


@router.post("/imports/excel", response_model=ImportResult)
async def excel_import(db: Db, user: CurrentUser, file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")): raise HTTPException(422, "يرجى رفع ملف Excel بصيغة xlsx أو xlsm")
    batch = import_workbook(db, await file.read(), file.filename, user.id)
    notify_roles(db, (Role.ADMIN, Role.MANAGER), "import_completed", "اكتمل استيراد Excel", f"تم استيراد {batch.imported_rows} صف ومراجعة {batch.review_rows} صف."); db.commit()
    await broker.publish("import.completed", {"batch_id": batch.id, "imported": batch.imported_rows, "review": batch.review_rows})
    return ImportResult(batch_id=batch.id, total_rows=batch.total_rows, imported_rows=batch.imported_rows, review_rows=batch.review_rows)


@router.get("/import-reviews")
def import_reviews(db: Db, _: CurrentUser, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100)):
    statement = select(ImportReview).where(ImportReview.status == "pending").order_by(ImportReview.created_at.desc())
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(statement.offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": rows, "total": total}


@router.post("/import-reviews/{review_id}/ignore")
def ignore_import_review(review_id: int, db: Db, _: User = Depends(require_roles(Role.ADMIN, Role.MANAGER))):
    review = db.get(ImportReview, review_id)
    if not review: raise HTTPException(404, "سجل المراجعة غير موجود")
    review.status = "ignored"; db.commit(); return {"ok": True}


@router.get("/dashboard/summary", response_model=DashboardSummary)
def summary(db: Db, _: CurrentUser):
    total = db.scalar(select(func.count()).select_from(Task)) or 0
    completed = db.scalar(select(func.count()).select_from(Task).where(Task.task_status == "مزال")) or 0
    review = db.scalar(select(func.count()).select_from(Task).where(Task.needs_review.is_(True))) or 0
    status_rows = db.execute(select(Task.task_status.label("label"), func.count().label("value")).group_by(Task.task_status)).mappings().all()
    return DashboardSummary(total_tasks=total, completion_rate=round(completed / total * 100, 1) if total else 0, delayed_tasks=0, needs_review=review, by_status=[dict(x) for x in status_rows], daily_trend=[])


@router.post("/assistant/chat", response_model=AssistantReply)
async def assistant_chat(payload: AssistantMessage, db: Db, _: CurrentUser):
    answer = await ask(db, payload.message)
    return AssistantReply(answer=answer, available=settings.ai_enabled and bool(settings.ai_api_key))


@router.get("/users", response_model=list[UserPublic])
def users(db: Db, _: User = Depends(require_roles(Role.ADMIN, Role.MANAGER))):
    return db.scalars(select(User).order_by(User.full_name)).all()


@router.post("/users", response_model=UserPublic, status_code=201)
async def create_user(payload: UserCreate, db: Db, _: User = Depends(require_roles(Role.ADMIN))):
    if UserRepository(db).by_username(payload.username): raise HTTPException(409, "اسم المستخدم مستخدم بالفعل")
    from app.core.security import hash_password
    user = User(username=payload.username, password_hash=hash_password(payload.password), full_name=payload.full_name, role=payload.role, city=payload.city)
    db.add(user); db.commit(); db.refresh(user)
    await broker.publish("user.created", {"id": user.id})
    return user


@router.get("/materials", response_model=list[MaterialPublic])
def materials(db: Db, _: User = Depends(require_roles(Role.ADMIN, Role.MANAGER))):
    return db.scalars(select(Material).order_by(Material.name)).all()


@router.post("/materials", response_model=MaterialPublic, status_code=201)
async def create_material(payload: MaterialCreate, db: Db, _: User = Depends(require_roles(Role.ADMIN, Role.MANAGER))):
    if db.scalar(select(Material).where(Material.name == payload.name)): raise HTTPException(409, "هذه المادة موجودة بالفعل")
    material = Material(**payload.model_dump()); db.add(material); db.commit(); db.refresh(material)
    await broker.publish("material.created", {"id": material.id})
    return material


@router.patch("/materials/{material_id}/quantity", response_model=MaterialPublic)
async def adjust_material(material_id: int, delta: int, db: Db, _: User = Depends(require_roles(Role.ADMIN, Role.MANAGER))):
    material = db.get(Material, material_id)
    if not material: raise HTTPException(404, "المادة غير موجودة")
    if material.quantity + delta < 0: raise HTTPException(422, "الكمية المطلوبة أكبر من المخزون")
    material.quantity += delta; db.commit(); db.refresh(material)
    await broker.publish("material.updated", {"id": material.id, "quantity": material.quantity})
    return material


@router.get("/assignments", response_model=list[AssignmentPublic])
def assignments(db: Db, user: CurrentUser, technician_id: int | None = None):
    statement = select(AssignedTask).where(AssignedTask.completed_at.is_(None))
    if user.role == Role.TECHNICIAN: statement = statement.where(AssignedTask.technician_id == user.id)
    elif technician_id: statement = statement.where(AssignedTask.technician_id == technician_id)
    return db.scalars(statement.order_by(AssignedTask.assigned_date.desc())).all()


@router.post("/assignments", response_model=AssignmentPublic, status_code=201)
async def assign(payload: AssignmentCreate, db: Db, user: User = Depends(require_roles(Role.ADMIN, Role.MANAGER))):
    if not db.get(User, payload.technician_id): raise HTTPException(422, "الفني غير موجود")
    assignment = AssignedTask(**payload.model_dump(exclude_none=True), assigned_by_id=user.id); db.add(assignment); db.commit(); db.refresh(assignment)
    db.add(Notification(user_id=assignment.technician_id, event_type="task_assigned", title="مهمة مسندة", message=f"أُسندت إليك المهمة {assignment.task_number}")); db.commit()
    await broker.publish("assignment.created", {"id": assignment.id, "technician_id": assignment.technician_id})
    return assignment


@router.post("/assignments/{assignment_id}/complete", response_model=AssignmentPublic)
async def complete_assignment(assignment_id: int, db: Db, user: CurrentUser):
    assignment = db.get(AssignedTask, assignment_id)
    if not assignment: raise HTTPException(404, "المهمة المسندة غير موجودة")
    if user.role == Role.TECHNICIAN and assignment.technician_id != user.id: raise HTTPException(403, "لا تملك صلاحية هذه المهمة")
    from datetime import UTC, datetime
    assignment.completed_at = datetime.now(UTC); db.commit(); db.refresh(assignment)
    await broker.publish("assignment.completed", {"id": assignment.id})
    return assignment


@router.get("/notifications")
def notifications(db: Db, user: CurrentUser):
    return db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(100)).all()


@router.post("/notifications/{notification_id}/read")
def read_notification(notification_id: int, db: Db, user: CurrentUser):
    notification = db.get(Notification, notification_id)
    if not notification or notification.user_id != user.id: raise HTTPException(404, "الإشعار غير موجود")
    notification.is_read = True; db.commit(); return {"ok": True}


@router.post("/daily-reports", status_code=201)
async def upload_daily_report(db: Db, user: CurrentUser, report_date: str, image: UploadFile = File(...)):
    from datetime import date
    try: parsed_date = date.fromisoformat(report_date); key, mime = await save_report_image(user.id, report_date, image)
    except ValueError as exc: raise HTTPException(422, str(exc))
    report = db.scalar(select(DailyReport).where(DailyReport.technician_id == user.id, DailyReport.report_date == parsed_date))
    if report: report.image_key, report.image_mime = key, mime
    else: report = DailyReport(technician_id=user.id, report_date=parsed_date, image_key=key, image_mime=mime); db.add(report)
    db.commit(); db.refresh(report)
    await broker.publish("daily_report.saved", {"id": report.id, "technician_id": user.id})
    return {"id": report.id, "report_date": report.report_date, "image_key": report.image_key}


@router.get("/daily-reports")
def daily_reports(db: Db, user: CurrentUser, technician_id: int | None = None):
    statement = select(DailyReport).order_by(DailyReport.report_date.desc())
    if user.role == Role.TECHNICIAN: statement = statement.where(DailyReport.technician_id == user.id)
    elif technician_id: statement = statement.where(DailyReport.technician_id == technician_id)
    return db.scalars(statement).all()


@router.get("/daily-reports/{report_id}/image")
def report_image(report_id: int, db: Db, user: CurrentUser):
    report = db.get(DailyReport, report_id)
    if not report or (user.role == Role.TECHNICIAN and report.technician_id != user.id): raise HTTPException(404, "التقرير غير موجود")
    try: path = report_path(report.image_key)
    except FileNotFoundError: raise HTTPException(404, "ملف التقرير غير موجود")
    return FileResponse(path, media_type=report.image_mime)


@router.websocket("/ws/events")
async def events(socket: WebSocket):
    await broker.connect(socket)
    try:
        while True: await socket.receive_text()
    except Exception: broker.disconnect(socket)
