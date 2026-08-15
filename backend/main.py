import os
from typing import Any, Dict, List, Optional, Union
from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from models import EmailLogModel, TaskModel, get_db, init_db
from schemas import (
    ALLOWED_ASSIGNEES,
    ALLOWED_CATEGORIES,
    ALLOWED_PRIORITIES,
    ChatRequest,
    ChatResponse,
    CreateTaskRequest,
    IngestEmailItem,
    IngestRequest,
    LLMDecision,
    TEAM_ROSTER,
    UpdateTaskRequest,
)
from services import classify_email, process_grounded_chat

load_dotenv()

app = FastAPI(title="Sales Inbox Task Router API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


@app.get("/")
def root_health_check():
    return {
        "status": "online",
        "service": "Sales Inbox Task Router API",
        "candidate_id": "priya.sharma@gmail.com",
        "docs": "/docs",
        "endpoints": {
            "users": "/users",
            "tasks": "/tasks?candidate_id=priya.sharma@gmail.com",
            "ingest": "POST /ingest",
            "chat": "POST /api/chat"
        }
    }


def validate_task_enums(data: dict):
    if "assignee_id" in data and data["assignee_id"] is not None:
        if data["assignee_id"] not in ALLOWED_ASSIGNEES:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_enum_value",
                    "field": "assignee_id",
                    "received": data["assignee_id"],
                    "allowed": ALLOWED_ASSIGNEES,
                },
            )
    if "category" in data and data["category"] is not None:
        if data["category"] not in ALLOWED_CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_enum_value",
                    "field": "category",
                    "received": data["category"],
                    "allowed": ALLOWED_CATEGORIES,
                },
            )
    if "priority" in data and data["priority"] is not None:
        if data["priority"] not in ALLOWED_PRIORITIES:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_enum_value",
                    "field": "priority",
                    "received": data["priority"],
                    "allowed": ALLOWED_PRIORITIES,
                },
            )


@app.get("/users")
def get_users():
    return TEAM_ROSTER


@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(payload: CreateTaskRequest, db: Session = Depends(get_db)):
    raw = payload.model_dump()
    validate_task_enums(raw)
    cid = payload.candidate_id.strip().lower()

    # Idempotency check: don't double create for same source_email_id & candidate_id
    existing = (
        db.query(TaskModel)
        .filter(
            TaskModel.source_email_id == payload.source_email_id,
            TaskModel.candidate_id == cid,
        )
        .first()
    )
    if existing:
        return {
            "task_id": existing.task_id,
            "candidate_id": existing.candidate_id,
            "source_email_id": existing.source_email_id,
            "created_at": existing.created_at.isoformat() + "+05:30",
        }

    task = TaskModel(
        candidate_id=cid,
        source_email_id=payload.source_email_id,
        thread_id=payload.thread_id,
        title=payload.title,
        description=payload.description,
        assignee_id=payload.assignee_id,
        category=payload.category,
        priority=payload.priority,
        due_date=payload.due_date,
        deal_value_inr=payload.deal_value_inr,
        company_name=payload.company_name,
        confidence=payload.confidence,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {
        "task_id": task.task_id,
        "candidate_id": task.candidate_id,
        "source_email_id": task.source_email_id,
        "created_at": task.created_at.isoformat() + "+05:30",
    }


@app.patch("/tasks/{task_id}")
def update_task(
    task_id: str, payload: UpdateTaskRequest, db: Session = Depends(get_db)
):
    raw = payload.model_dump(exclude_unset=True)
    validate_task_enums(raw)

    task = db.query(TaskModel).filter(TaskModel.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    for k, v in raw.items():
        setattr(task, k, v)
    task.update_count += 1

    db.commit()
    db.refresh(task)

    return {
        "task_id": task.task_id,
        "candidate_id": task.candidate_id,
        "source_email_id": task.source_email_id,
        "thread_id": task.thread_id,
        "title": task.title,
        "description": task.description,
        "assignee_id": task.assignee_id,
        "category": task.category,
        "priority": task.priority,
        "due_date": task.due_date,
        "deal_value_inr": task.deal_value_inr,
        "company_name": task.company_name,
        "confidence": task.confidence,
        "created_at": task.created_at.isoformat() + "+05:30" if task.created_at else None,
        "updated_at": task.updated_at.isoformat() + "+05:30" if task.updated_at else None,
    }


@app.get("/tasks")
def list_tasks(
    candidate_id: str = Query(...),
    thread_id: Optional[str] = None,
    source_email_id: Optional[str] = None,
    assignee_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    cid = candidate_id.strip().lower()
    query = db.query(TaskModel).filter(TaskModel.candidate_id == cid)
    if thread_id:
        query = query.filter(TaskModel.thread_id == thread_id)
    if source_email_id:
        query = query.filter(TaskModel.source_email_id == source_email_id)
    if assignee_id:
        query = query.filter(TaskModel.assignee_id == assignee_id)

    tasks = query.order_by(TaskModel.created_at.desc()).all()
    return [
        {
            "task_id": t.task_id,
            "candidate_id": t.candidate_id,
            "source_email_id": t.source_email_id,
            "thread_id": t.thread_id,
            "title": t.title,
            "description": t.description,
            "assignee_id": t.assignee_id,
            "category": t.category,
            "priority": t.priority,
            "due_date": t.due_date,
            "deal_value_inr": t.deal_value_inr,
            "company_name": t.company_name,
            "confidence": t.confidence,
            "created_at": t.created_at.isoformat() + "+05:30" if t.created_at else None,
        }
        for t in tasks
    ]


@app.get("/tasks/{task_id}")
def get_single_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task_id": task.task_id,
        "candidate_id": task.candidate_id,
        "source_email_id": task.source_email_id,
        "thread_id": task.thread_id,
        "title": task.title,
        "description": task.description,
        "assignee_id": task.assignee_id,
        "category": task.category,
        "priority": task.priority,
        "due_date": task.due_date,
        "deal_value_inr": task.deal_value_inr,
        "company_name": task.company_name,
        "confidence": task.confidence,
        "created_at": task.created_at.isoformat() + "+05:30" if task.created_at else None,
    }


@app.delete("/tasks/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"status": "deleted", "task_id": task_id}


@app.post("/ingest")
def ingest_emails(
    payload: Union[IngestRequest, List[IngestEmailItem]] = Body(...),
    db: Session = Depends(get_db),
):
    if isinstance(payload, list):
        candidate_id = "priya.sharma@gmail.com"
        email_list = payload
    else:
        candidate_id = (payload.candidate_id or "priya.sharma@gmail.com").strip().lower()
        email_list = payload.emails

    created = 0
    updated = 0
    skipped = 0
    errors = []

    for email in email_list:
        try:
            # Idempotency check: skip already logged emails
            existing_log = (
                db.query(EmailLogModel)
                .filter(
                    EmailLogModel.email_id == email.email_id,
                    EmailLogModel.candidate_id == candidate_id,
                )
                .first()
            )
            if existing_log:
                continue

            decision: LLMDecision = classify_email(email)

            # 1. Handle noise (out of office, newsletter, spam)
            if decision.is_noise:
                skipped += 1
                db.add(
                    EmailLogModel(
                        email_id=email.email_id,
                        candidate_id=candidate_id,
                        thread_id=email.thread_id,
                        action_taken="skipped",
                        skip_reason=decision.noise_reason or "vendor_spam",
                        category_detected=decision.category,
                        raw_subject=email.subject,
                    )
                )
                db.commit()
                continue

            # 2. Thread reconciliation check
            existing_task = (
                db.query(TaskModel)
                .filter(
                    TaskModel.thread_id == email.thread_id,
                    TaskModel.candidate_id == candidate_id,
                )
                .first()
            )

            if existing_task:
                # Update task details based on reply
                if decision.priority:
                    existing_task.priority = decision.priority
                if decision.due_date:
                    existing_task.due_date = decision.due_date
                if decision.deal_value_inr:
                    existing_task.deal_value_inr = decision.deal_value_inr
                if decision.description:
                    existing_task.description = decision.description
                existing_task.update_count += 1

                db.add(
                    EmailLogModel(
                        email_id=email.email_id,
                        candidate_id=candidate_id,
                        thread_id=email.thread_id,
                        action_taken="updated",
                        skip_reason=None,
                        category_detected=decision.category,
                        raw_subject=email.subject,
                    )
                )
                updated += 1
                db.commit()
            else:
                # 3. Create new task
                new_task = TaskModel(
                    candidate_id=candidate_id,
                    source_email_id=email.email_id,
                    thread_id=email.thread_id,
                    title=decision.title,
                    description=decision.description,
                    assignee_id=decision.assignee_id,
                    category=decision.category,
                    priority=decision.priority,
                    due_date=decision.due_date,
                    deal_value_inr=decision.deal_value_inr,
                    company_name=decision.company_name,
                    confidence=decision.confidence,
                )
                db.add(new_task)
                db.add(
                    EmailLogModel(
                        email_id=email.email_id,
                        candidate_id=candidate_id,
                        thread_id=email.thread_id,
                        action_taken="created",
                        skip_reason=None,
                        category_detected=decision.category,
                        raw_subject=email.subject,
                    )
                )
                created += 1
                db.commit()

        except Exception as e:
            errors.append({"email_id": email.email_id, "error": str(e)})

    return {
        "processed": created + updated + skipped + len(errors),
        "tasks_created": created,
        "tasks_updated": updated,
        "skipped": skipped,
        "errors": errors,
    }


@app.get("/api/tasks")
def get_api_tasks(
    candidate_id: str = Query(default="priya.sharma@gmail.com"),
    db: Session = Depends(get_db),
):
    cid = candidate_id.strip().lower()
    tasks = db.query(TaskModel).filter(TaskModel.candidate_id == cid).all()
    logs = db.query(EmailLogModel).filter(EmailLogModel.candidate_id == cid).all()
    return {
        "tasks": [
            {
                "task_id": t.task_id,
                "candidate_id": t.candidate_id,
                "source_email_id": t.source_email_id,
                "thread_id": t.thread_id,
                "title": t.title,
                "description": t.description,
                "assignee_id": t.assignee_id,
                "category": t.category,
                "priority": t.priority,
                "due_date": t.due_date,
                "deal_value_inr": t.deal_value_inr,
                "company_name": t.company_name,
                "confidence": t.confidence,
                "update_count": t.update_count,
                "created_at": t.created_at.isoformat() + "+05:30" if t.created_at else None,
            }
            for t in tasks
        ],
        "email_logs": [
            {
                "email_id": l.email_id,
                "candidate_id": l.candidate_id,
                "thread_id": l.thread_id,
                "action_taken": l.action_taken,
                "skip_reason": l.skip_reason,
                "category_detected": l.category_detected,
                "raw_subject": l.raw_subject,
                "created_at": l.created_at.isoformat() + "+05:30" if l.created_at else None,
            }
            for l in logs
        ],
    }


@app.get("/api/stats")
def get_api_stats(
    candidate_id: str = Query(default="priya.sharma@gmail.com"),
    db: Session = Depends(get_db),
):
    cid = candidate_id.strip().lower()
    tasks = db.query(TaskModel).filter(TaskModel.candidate_id == cid).all()
    logs = db.query(EmailLogModel).filter(EmailLogModel.candidate_id == cid).all()

    category_counts = {c: 0 for c in ALLOWED_CATEGORIES}
    assignee_counts = {a: 0 for a in ALLOWED_ASSIGNEES}

    for t in tasks:
        category_counts[t.category] = category_counts.get(t.category, 0) + 1
        assignee_counts[t.assignee_id] = assignee_counts.get(t.assignee_id, 0) + 1

    return {
        "candidate_id": cid,
        "processed": len(logs),
        "tasks_created": len(tasks),
        "tasks_updated": sum(1 for l in logs if l.action_taken == "updated"),
        "skipped": sum(1 for l in logs if l.action_taken == "skipped"),
        "categories": category_counts,
        "assignees": assignee_counts,
    }


@app.post("/api/chat")
def chat_endpoint(payload: ChatRequest, db: Session = Depends(get_db)):
    try:
        cid = (payload.candidate_id or "priya.sharma@gmail.com").strip().lower()
        tasks = db.query(TaskModel).filter(TaskModel.candidate_id == cid).all()
        logs = db.query(EmailLogModel).filter(EmailLogModel.candidate_id == cid).all()

        category_counts = {c: 0 for c in ALLOWED_CATEGORIES}
        assignee_counts = {a: 0 for a in ALLOWED_ASSIGNEES}

        for t in tasks:
            category_counts[t.category] = category_counts.get(t.category, 0) + 1
            assignee_counts[t.assignee_id] = (
                assignee_counts.get(t.assignee_id, 0) + 1
            )

        task_records = [
            {
                "task_id": t.task_id,
                "source_email_id": t.source_email_id,
                "thread_id": t.thread_id,
                "title": t.title,
                "description": t.description,
                "assignee_id": t.assignee_id,
                "category": t.category,
                "priority": t.priority,
                "due_date": t.due_date,
                "deal_value_inr": t.deal_value_inr,
                "company_name": t.company_name,
                "confidence": t.confidence,
                "update_count": t.update_count,
            }
            for t in tasks
        ]

        skipped_spam = (
            db.query(EmailLogModel)
            .filter(
                EmailLogModel.candidate_id == cid,
                EmailLogModel.skip_reason == "vendor_spam",
            )
            .count()
        )

        rfp_tasks = [t for t in tasks if t.category == "enterprise_rfp"]

        ground_truth = {
            "candidate_id": cid,
            "team_roster": TEAM_ROSTER["team"],
            "total_emails_processed": len(logs),
            "total_tasks_created": len(tasks),
            "category_counts": category_counts,
            "assignee_counts": assignee_counts,
            "skipped_marketing_lookalike_spam": skipped_spam,
            "tasks": task_records,
            "email_logs": [
                {
                    "email_id": l.email_id,
                    "action_taken": l.action_taken,
                    "skip_reason": l.skip_reason,
                    "category_detected": l.category_detected,
                }
                for l in logs
            ],
            "rfp_total_deal_value_inr": sum(
                t.deal_value_inr for t in rfp_tasks if t.deal_value_inr
            ),
            "rfps_with_no_stated_value": sum(
                1 for t in rfp_tasks if t.deal_value_inr is None
            ),
        }

        return process_grounded_chat(ground_truth, payload.query)

    except Exception as e:
        return {
            "answer": (
                "I could not process that specific query against the database."
                f" Error: {str(e)}"
            ),
            "supporting_data": {},
        }