import logging
from datetime import date, timedelta
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, WebSocket
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from app.api.deps import CurrentUser, Db, require_roles
from app.core.config import get_settings
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models import AssignedTask, DailyReport, ImportReview, Material, Notification, Role, Task, User
from app.repositories import TaskRepository, UserRepository
from app.schemas import AssignmentCreate, AssignmentPublic, AssistantMessage, AssistantReply, DailyReportPublic, DashboardSummary, DeveloperStatus, ImportResult, ImportReviewPublic, ImportReviewRepair, LoginRequest, MaterialCreate, MaterialPublic, NotificationPublic, Page, PasswordChange, RefreshRequest, TaskCreate, TaskPublic, TaskReportSummary, TaskUpdate, TokenPair, UserCreate, UserPublic, UserUpdate
from app.services.assistant import ask
from app.services.notifications import notify_roles
from app.services.report_storage import report_bytes, save_report_image
from app.services.events import broker
from app.services.importer import DEFAULT_STATUS, DEFAULT_SUBSCRIPTION, import_workbook

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


@router.post("/auth/change-password", status_code=204)
def change_password(payload: PasswordChange, user: CurrentUser, db: Db):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(422, "كلمة المرور الحالية غير صحيحة")
    if payload.current_password == payload.new_password:
        raise HTTPException(422, "اختر كلمة مرور جديدة مختلفة عن الحالية")
    user.password_hash = hash_password(payload.new_password)
    db.commit()


@router.get("/tasks", response_model=Page[TaskPublic])
def tasks(db: Db, _: CurrentUser, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), search: str | None = None, status: str | None = None):
    items, total = TaskRepository(db).list(page, page_size, search, status)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("/tasks", response_model=TaskPublic, status_code=201)
async def create_task(payload: TaskCreate, db: Db, user: CurrentUser):
    task = Task(**payload.model_dump(exclude_none=True)); db.add(task); db.commit(); db.refresh(task)
    notify_roles(db, (Role.ADMIN,), "task_created", "مهمة جديدة", f"تمت إضافة المهمة {task.task_number}"); db.commit()
    await broker.publish("task.created", {"id": task.id, "actor": user.full_name})
    return task


@router.patch("/tasks/{task_id}", response_model=TaskPublic)
async def update_task(task_id: int, payload: TaskUpdate, db: Db, user: User = Depends(require_roles(Role.ADMIN))):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "المهمة غير موجودة")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    notify_roles(db, (Role.ADMIN,), "task_updated", "تم تعديل مهمة", f"تم تعديل المهمة {task.task_number}")
    db.commit()
    await broker.publish("task.updated", {"id": task.id, "actor": user.full_name})
    return task


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int, db: Db, _: User = Depends(require_roles(Role.ADMIN))):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "المهمة غير موجودة")
    db.delete(task)
    db.commit()


@router.post("/imports/excel", response_model=ImportResult)
async def excel_import(db: Db, user: CurrentUser, file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")): raise HTTPException(422, "يرجى رفع ملف Excel بصيغة xlsx أو xlsm")
    if file.size is not None and file.size > settings.max_upload_bytes:
        raise HTTPException(413, "حجم ملف Excel يتجاوز الحد المسموح")
    contents = await file.read()
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(413, "حجم ملف Excel يتجاوز الحد المسموح")
    batch = import_workbook(db, contents, file.filename, user.id)
    notify_roles(db, (Role.ADMIN,), "import_completed", "اكتمل استيراد Excel", f"تم استيراد {batch.imported_rows} صف ومراجعة {batch.review_rows} صف."); db.commit()
    await broker.publish("import.completed", {"batch_id": batch.id, "imported": batch.imported_rows, "review": batch.review_rows})
    return ImportResult(batch_id=batch.id, total_rows=batch.total_rows, imported_rows=batch.imported_rows, review_rows=batch.review_rows)


@router.get("/import-reviews", response_model=Page[ImportReviewPublic])
def import_reviews(db: Db, _: User = Depends(require_roles(Role.ADMIN)), page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100)):
    statement = select(ImportReview).where(ImportReview.status == "pending").order_by(ImportReview.created_at.desc())
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(statement.offset((page - 1) * page_size).limit(page_size)).all()
    # Page is deliberately reused as the stable pagination contract across tables.
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


@router.patch("/import-reviews/{review_id}", response_model=ImportReviewPublic)
def repair_import_review(review_id: int, payload: ImportReviewRepair, db: Db, _: User = Depends(require_roles(Role.ADMIN))):
    """Store an operator correction. IDs are intentionally absent from this payload."""
    review = db.get(ImportReview, review_id)
    if not review: raise HTTPException(404, "سجل المراجعة غير موجود")
    if review.status != "pending": raise HTTPException(409, "هذا السجل لم يعد بانتظار المراجعة")
    changes = payload.model_dump(exclude_unset=True)
    for field in ("task_number", "technician_name", "subscription_number", "task_type"):
        if field in changes:
            setattr(review, field, changes[field])
    review.action_taken = "corrected_by_operator"
    db.commit(); db.refresh(review)
    return review


@router.post("/import-reviews/{review_id}/reinsert")
async def reinsert_import_review(review_id: int, payload: ImportReviewRepair, db: Db, _: User = Depends(require_roles(Role.ADMIN))):
    """Retry exactly one corrected row, safely preserving the review on failure."""
    review = db.get(ImportReview, review_id)
    if not review: raise HTTPException(404, "سجل المراجعة غير موجود")
    if review.status != "pending": raise HTTPException(409, "هذا السجل لم يعد بانتظار المراجعة")
    values = payload.model_dump(exclude_none=True)
    task_number = values.get("task_number") or review.task_number
    if not task_number:
        return {"ok": False, "message": "رقم المهمة مطلوب قبل إعادة الإدراج"}
    try:
        task = Task(
            technician_name=values.get("technician_name") or review.technician_name or "غير مسجل",
            task_number=task_number,
            subscription_number=values.get("subscription_number") or review.subscription_number or DEFAULT_SUBSCRIPTION,
            task_type=values.get("task_type") or review.task_type or "تقني",
            task_status=values.get("task_status") or DEFAULT_STATUS,
            city=values.get("city"), notes=values.get("notes"),
            execution_date=values.get("execution_date") or date.today(),
        )
        with db.begin_nested():
            db.add(task); db.flush()
        review.status = "resolved"; review.action_taken = "reinserted_by_operator"
        db.commit()
    except Exception as exc:
        logger = logging.getLogger(__name__)
        logger.exception("Import review reinsertion failed safely", extra={"review_id": review_id})
        db.rollback()
        review = db.get(ImportReview, review_id)
        if review:
            review.exception_type = type(exc).__name__
            review.error_message = str(exc)[:4000]
            review.postgres_message = str(exc)[:4000] if isinstance(exc, SQLAlchemyError) else None
            review.action_taken = "reinsertion_failed_kept_for_review"
            db.commit()
        return {"ok": False, "message": "تعذرت إعادة الإدراج؛ بقي السجل في المراجعة."}
    await broker.publish("import.review.reinserted", {"review_id": review_id})
    return {"ok": True, "task_id": task.id}


@router.post("/import-reviews/{review_id}/ignore")
def ignore_import_review(review_id: int, db: Db, _: User = Depends(require_roles(Role.ADMIN))):
    review = db.get(ImportReview, review_id)
    if not review: raise HTTPException(404, "سجل المراجعة غير موجود")
    review.status = "ignored"; db.commit(); return {"ok": True}


@router.get("/dashboard/summary", response_model=DashboardSummary)
def summary(db: Db, _: CurrentUser):
    total = db.scalar(select(func.count()).select_from(Task)) or 0
    completed = db.scalar(select(func.count()).select_from(Task).where(Task.task_status == "مزال")) or 0
    delayed = db.scalar(select(func.count()).select_from(Task).where(Task.task_status == "عائق")) or 0
    review = db.scalar(
        select(func.count()).select_from(ImportReview).where(ImportReview.status == "pending")
    ) or 0
    status_rows = db.execute(select(Task.task_status.label("label"), func.count().label("value")).group_by(Task.task_status)).mappings().all()
    daily_rows = db.execute(
        select(Task.execution_date.label("label"), func.count().label("value"))
        .group_by(Task.execution_date).order_by(Task.execution_date.desc()).limit(14)
    ).mappings().all()
    technician_rows = db.execute(
        select(Task.technician_name.label("label"), func.count().label("value"))
        .where(Task.technician_name != "غير مسجل").group_by(Task.technician_name)
        .order_by(func.count().desc()).limit(5)
    ).mappings().all()
    latest = db.scalars(select(Task).order_by(Task.created_at.desc(), Task.id.desc()).limit(8)).all()
    return DashboardSummary(
        total_tasks=total, completion_rate=round(completed / total * 100, 1) if total else 0,
        delayed_tasks=delayed, needs_review=review, by_status=[dict(x) for x in status_rows],
        daily_trend=[{"label": row["label"].isoformat(), "value": row["value"]} for row in reversed(daily_rows)],
        latest_tasks=latest, top_technicians=[dict(row) for row in technician_rows],
    )


@router.get("/reports/tasks", response_model=TaskReportSummary)
def task_report(db: Db, _: User = Depends(require_roles(Role.ADMIN)), city: str = Query(..., min_length=1, max_length=120)):
    """City-scoped report using aggregated queries and a small latest-tasks window."""
    statement = select(Task).where(Task.city == city)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    completed = db.scalar(select(func.count()).select_from(Task).where(Task.city == city, Task.task_status == "مزال")) or 0
    blocked = db.scalar(select(func.count()).select_from(Task).where(Task.city == city, Task.task_status == "عائق")) or 0
    statuses = db.execute(select(Task.task_status.label("label"), func.count().label("value")).where(Task.city == city).group_by(Task.task_status)).mappings().all()
    latest = db.scalars(statement.order_by(Task.execution_date.desc(), Task.id.desc()).limit(10)).all()
    return TaskReportSummary(city=city, total_tasks=total, completed_tasks=completed, blocked_tasks=blocked, completion_rate=round(completed / total * 100, 1) if total else 0, by_status=[dict(row) for row in statuses], latest_tasks=latest)


@router.get("/developer/status", response_model=DeveloperStatus)
def developer_status(db: Db, _: User = Depends(require_roles(Role.ADMIN))):
    return DeveloperStatus(
        environment=settings.environment,
        total_users=db.scalar(select(func.count()).select_from(User)) or 0,
        total_tasks=db.scalar(select(func.count()).select_from(Task)) or 0,
        pending_import_reviews=db.scalar(select(func.count()).select_from(ImportReview).where(ImportReview.status == "pending")) or 0,
        unread_notifications=db.scalar(select(func.count()).select_from(Notification).where(Notification.is_read.is_(False))) or 0,
        ai_enabled=settings.ai_enabled and bool(settings.ai_api_key),
    )


@router.post("/assistant/chat", response_model=AssistantReply)
async def assistant_chat(payload: AssistantMessage, db: Db, _: CurrentUser):
    answer = await ask(db, payload.message)
    return AssistantReply(answer=answer, available=settings.ai_enabled and bool(settings.ai_api_key))


@router.get("/users", response_model=list[UserPublic])
def users(db: Db, _: User = Depends(require_roles(Role.ADMIN))):
    return db.scalars(select(User).order_by(User.full_name)).all()


@router.post("/users", response_model=UserPublic, status_code=201)
async def create_user(payload: UserCreate, db: Db, _: User = Depends(require_roles(Role.ADMIN))):
    if UserRepository(db).by_username(payload.username): raise HTTPException(409, "اسم المستخدم مستخدم بالفعل")
    if payload.role not in {Role.ADMIN, Role.TECHNICIAN}:
        raise HTTPException(422, "الدور المحدد غير صالح")
    from app.core.security import hash_password
    user = User(username=payload.username, password_hash=hash_password(payload.password), full_name=payload.full_name, role=payload.role, city=payload.city)
    db.add(user); db.commit(); db.refresh(user)
    notify_roles(db, (Role.ADMIN,), "user_created", "مستخدم جديد", f"تمت إضافة المستخدم {user.full_name}")
    db.commit()
    await broker.publish("user.created", {"id": user.id})
    return user


@router.patch("/users/{user_id}", response_model=UserPublic)
async def update_user(user_id: int, payload: UserUpdate, db: Db, _: User = Depends(require_roles(Role.ADMIN))):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "المستخدم غير موجود")
    if payload.role is not None and payload.role not in {Role.ADMIN, Role.TECHNICIAN}:
        raise HTTPException(422, "الدور المحدد غير صالح")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    await broker.publish("user.updated", {"id": user.id})
    return user


@router.delete("/users/{user_id}", status_code=204)
async def deactivate_user(user_id: int, db: Db, actor: User = Depends(require_roles(Role.ADMIN))):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "المستخدم غير موجود")
    if user.id == actor.id:
        raise HTTPException(422, "لا يمكن تعطيل حسابك الحالي")
    user.is_active = False
    db.commit()
    await broker.publish("user.deactivated", {"id": user.id})


@router.get("/materials", response_model=list[MaterialPublic])
def materials(db: Db, _: User = Depends(require_roles(Role.ADMIN))):
    return db.scalars(select(Material).order_by(Material.name)).all()


@router.post("/materials", response_model=MaterialPublic, status_code=201)
async def create_material(payload: MaterialCreate, db: Db, _: User = Depends(require_roles(Role.ADMIN))):
    if db.scalar(select(Material).where(Material.name == payload.name)): raise HTTPException(409, "هذه المادة موجودة بالفعل")
    material = Material(**payload.model_dump()); db.add(material); db.commit(); db.refresh(material)
    await broker.publish("material.created", {"id": material.id})
    return material


@router.patch("/materials/{material_id}/quantity", response_model=MaterialPublic)
async def adjust_material(material_id: int, delta: int, db: Db, _: User = Depends(require_roles(Role.ADMIN))):
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
async def assign(payload: AssignmentCreate, db: Db, user: User = Depends(require_roles(Role.ADMIN))):
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


@router.get("/notifications", response_model=list[NotificationPublic])
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


@router.get("/daily-reports", response_model=list[DailyReportPublic])
def daily_reports(db: Db, user: CurrentUser, technician_id: int | None = None):
    statement = select(DailyReport).order_by(DailyReport.report_date.desc())
    if user.role == Role.TECHNICIAN: statement = statement.where(DailyReport.technician_id == user.id)
    elif technician_id: statement = statement.where(DailyReport.technician_id == technician_id)
    return db.scalars(statement).all()


@router.get("/daily-reports/{report_id}/image")
def report_image(report_id: int, db: Db, user: CurrentUser):
    report = db.get(DailyReport, report_id)
    if not report or (user.role == Role.TECHNICIAN and report.technician_id != user.id): raise HTTPException(404, "التقرير غير موجود")
    try: content = report_bytes(report.image_key)
    except FileNotFoundError: raise HTTPException(404, "ملف التقرير غير موجود")
    return Response(content=content, media_type=report.image_mime)


@router.websocket("/ws/events")
async def events(socket: WebSocket):
    """Authenticated event stream; unauthenticated sockets are never accepted."""
    token = socket.headers.get("sec-websocket-protocol")
    if not token:
        await socket.close(code=1008, reason="Authentication required")
        return
    try:
        decode_token(token, "access")
    except Exception:
        await socket.close(code=1008, reason="Invalid session")
        return
    await broker.connect(socket, subprotocol=token)
    try:
        while True: await socket.receive_text()
    except Exception: broker.disconnect(socket)
