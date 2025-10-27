from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime
from app.db import models
from app.db.database import get_db
from app.deps import get_current_user

router = APIRouter()


# --------------------------------------------
# 🔒 Utility: Access control
# --------------------------------------------
def require_manager_or_admin(current_user: models.User):
    if not current_user.role or current_user.role.name not in ("admin", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to admins and managers only"
        )


# --------------------------------------------
# 📊 Task Counts by Status (Overall)
# --------------------------------------------
@router.get("/task_counts")
def task_counts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    require_manager_or_admin(current_user)

    q = (
        db.query(models.Task.status, func.count(models.Task.id))
        .group_by(models.Task.status)
        .all()
    )

    result = {status: count for status, count in q}

    # Include total count and percent breakdown
    total_tasks = sum(result.values()) or 0
    for key in result:
        result[key] = {
            "count": result[key],
            "percent": round((result[key] / total_tasks * 100), 2) if total_tasks > 0 else 0.0
        }

    result["total_tasks"] = total_tasks
    return result


# --------------------------------------------
# 📈 Project Progress (per project)
# --------------------------------------------
@router.get("/project_progress/{project_id}")
def project_progress(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    require_manager_or_admin(current_user)

    total = db.query(func.count(models.Task.id)).filter(models.Task.project_id == project_id).scalar() or 0
    done = db.query(func.count(models.Task.id)).filter(
        models.Task.project_id == project_id, models.Task.status == "done"
    ).scalar() or 0
    in_progress = db.query(func.count(models.Task.id)).filter(
        models.Task.project_id == project_id, models.Task.status == "in_progress"
    ).scalar() or 0
    todo = total - (done + in_progress)

    progress = (done / total * 100) if total > 0 else 0.0

    return {
        "project_id": project_id,
        "total_tasks": total,
        "todo": todo,
        "in_progress": in_progress,
        "done": done,
        "progress_percent": round(progress, 2)
    }


# --------------------------------------------
# ⏰ Overdue Tasks by Project
# --------------------------------------------
@router.get("/overdue_by_project")
def overdue_by_project(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    require_manager_or_admin(current_user)

    now = datetime.utcnow()

    results = (
        db.query(
            models.Project.id.label("project_id"),
            models.Project.title.label("project_title"),
            func.count(models.Task.id).label("overdue_tasks")
        )
        .join(models.Task, models.Task.project_id == models.Project.id)
        .filter(models.Task.due_date < now, models.Task.status != "done")
        .group_by(models.Project.id)
        .all()
    )

    return [
        {
            "project_id": r.project_id,
            "project_title": r.project_title,
            "overdue_tasks": r.overdue_tasks
        }
        for r in results
    ]


# --------------------------------------------
# 🧾 Summary Dashboard (NEW)
# --------------------------------------------
@router.get("/summary")
def summary_dashboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    require_manager_or_admin(current_user)

    total_projects = db.query(func.count(models.Project.id)).scalar() or 0
    total_tasks = db.query(func.count(models.Task.id)).scalar() or 0
    total_users = db.query(func.count(models.User.id)).scalar() or 0

    overdue_tasks = db.query(func.count(models.Task.id)).filter(
        models.Task.due_date < datetime.utcnow(),
        models.Task.status != "done"
    ).scalar() or 0

    completed_tasks = db.query(func.count(models.Task.id)).filter(
        models.Task.status == "done"
    ).scalar() or 0

    progress_percent = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0

    return {
        "totals": {
            "projects": total_projects,
            "tasks": total_tasks,
            "users": total_users
        },
        "completed_tasks": completed_tasks,
        "overdue_tasks": overdue_tasks,
        "overall_progress_percent": round(progress_percent, 2)
    }
