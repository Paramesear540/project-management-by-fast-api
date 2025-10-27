from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import models, schemas
from app.db.database import get_db
from app.deps import get_current_user
from typing import List
from sqlalchemy.orm import joinedload

router = APIRouter()

@router.post('/', response_model=schemas.CommentOut)
def add_comment(
    comment_in: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    task = db.query(models.Task).filter(models.Task.id == comment_in.task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Task not found')
    
    # Only the assigned developer can comment
    if current_user.role.name == "developer" and task.assignee_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted to comment on this task")
    
    comment = models.Comment(content=comment_in.content, task=task, author=current_user)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment

@router.get('/task/{task_id}', response_model=List[schemas.CommentOut])
def list_comments(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(404, 'Task not found')

    comments = (
        db.query(models.Comment)
        .options(joinedload(models.Comment.author))  # ✅ eager-load author
        .filter(models.Comment.task_id == task_id)
        .all()
    )

    return comments  # FastAPI + Pydantic will serialize the nested author


@router.delete('/{comment_id}', status_code=204)
def delete_comment(comment_id:int, db:Session=Depends(get_db), current_user:models.User=Depends(get_current_user)):
    comment = db.query(models.Comment).filter(models.Comment.id==comment_id).first()
    if not comment: raise HTTPException(404, 'Comment not found')
    if current_user.role.name != 'admin' and comment.author_id != current_user.id:
        raise HTTPException(403, 'Not permitted')
    db.delete(comment); db.commit()
    return {}