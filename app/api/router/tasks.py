from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import models, schemas
from app.db.database import get_db
from app.deps import get_current_user
from datetime import datetime

router = APIRouter()


@router.post('/', response_model=schemas.TaskOut)
def create_task(
    task_in: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Use .name instead of .value
    if not current_user.role or current_user.role.name not in ('admin', 'manager'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not permitted')

    project = db.query(models.Project).filter(models.Project.id == task_in.project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')

    task = models.Task(
        title=task_in.title,
        description=task_in.description,
        due_date=task_in.due_date,
        project=project
    )

    if task_in.assignee_id:
        assignee = db.query(models.User).filter(models.User.id == task_in.assignee_id).first()
        if assignee:
            task.assignee = assignee

    db.add(task)
    db.commit()
    db.refresh(task)
    return task

@router.get('/overdue')
def overdue_tasks(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    now = datetime.utcnow()
    return db.query(models.Task).filter(
        models.Task.due_date < now,
        models.Task.status != 'done'
    ).all()

@router.get('/{task_id}', response_model=schemas.TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    # Optional: restrict access based on roles
    if current_user.role.name == 'developer' and task.assignee_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")
    return task


@router.put('/{task_id}', response_model=schemas.TaskOut)
def update_task(
    task_id: int,
    task_in: schemas.TaskUpdate,  # new Pydantic schema for optional updates
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if current_user.role.name not in ('admin', 'manager'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")

    if task_in.title is not None:
        task.title = task_in.title
    if task_in.description is not None:
        task.description = task_in.description
    if task_in.due_date is not None:
        task.due_date = task_in.due_date
    if task_in.assignee_id is not None:
        assignee = db.query(models.User).filter(models.User.id == task_in.assignee_id).first()
        if assignee:
            task.assignee = assignee

    db.commit()
    db.refresh(task)
    return task

@router.get('/')
def list_tasks(
    project_id: int = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.Task)
    if project_id:
        query = query.filter(models.Task.project_id == project_id)
    
    # Developers see only their tasks
    if current_user.role.name == 'developer':
        query = query.filter(models.Task.assignee_id == current_user.id)
    
    return query.all()

@router.put('/{task_id}/status')
def update_task_status(
    task_id: int,
    status_in: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Task not found')

    if current_user.role and current_user.role.name == 'developer' and task.assignee_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not permitted')

    new_status = status_in.get('status')
    if new_status not in ('todo', 'in_progress', 'done'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid status')

    task.status = new_status
    db.commit()
    db.refresh(task)
    return {'ok': True, 'status': task.status}

@router.put("/{task_id}/deadline")
def update_task_deadline(
    task_id: int,
    new_deadline: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Only admins/managers or task assignee can update the deadline
    if current_user.role and current_user.role.name not in ("admin", "manager") and task.assignee_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")

    due_date = new_deadline.get("due_date")
    if not due_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing due_date")

    task.due_date = due_date
    db.commit()
    db.refresh(task)
    return {"ok": True, "task_id": task.id, "due_date": task.due_date}

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Only admins or managers can delete tasks
    if current_user.role and current_user.role.name not in ("admin", "manager"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")

    db.delete(task)
    db.commit()
    return {"ok": True, "message": "Task deleted successfully"}


