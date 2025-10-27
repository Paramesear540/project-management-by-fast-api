from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.db import models, schemas
from app.db.database import get_db
from app.deps import get_current_user
from typing import List

router = APIRouter()


# ---------------------------
# CREATE PROJECT
# ---------------------------
@router.post('/', response_model=schemas.ProjectOut)
def create_project(
    project_in: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role.name not in ('admin', 'manager'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not permitted')

    project = models.Project(title=project_in.title, description=project_in.description)

    if project_in.member_ids:
        members = db.query(models.User).filter(models.User.id.in_(project_in.member_ids)).all()
        if len(members) != len(set(project_in.member_ids)):
            existing_ids = [m.id for m in members]
            invalid_ids = list(set(project_in.member_ids) - set(existing_ids))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid member IDs: {invalid_ids}"
            )
        project.members = members

    db.add(project)
    db.commit()
    db.refresh(project)
    return project


# ---------------------------
# LIST ALL PROJECTS
# ---------------------------
@router.get('/', response_model=List[schemas.ProjectOut])
def list_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.Project).all()


# ---------------------------
# GET PROJECTS PROGRESS
# ---------------------------
@router.get("/progress", response_model=List[schemas.ProjectProgress])
@router.get("/progress/", response_model=List[schemas.ProjectProgress])
def get_project_progress(db: Session = Depends(get_db)):
    result = (
        db.query(
            models.Task.project_id,
            func.count(models.Task.id).label("total"),
            func.sum(case((models.Task.status == 'done', 1), else_=0)).label("completed")
        )
        .group_by(models.Task.project_id)
        .all()
    )

    progress_list = []
    for proj_id, total, completed in result:
        total = int(total or 0)
        completed = int(completed or 0)
        completion_percent = (completed / total * 100) if total > 0 else 0.0
        progress_list.append(
            schemas.ProjectProgress(
                project_id=int(proj_id),
                total_tasks=total,
                completed_tasks=completed,
                completion_percent=completion_percent
            )
        )

    return progress_list

# ---------------------------
# GET USER PROJECTS
# ---------------------------
@router.get("/user", response_model=List[schemas.ProjectOut])
@router.get("/user/", response_model=List[schemas.ProjectOut])
def get_user_projects(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    member_projects = (
        db.query(models.Project)
        .join(models.Project.members)
        .filter(models.User.id == current_user.id)
        .all()
    )

    task_projects = (
        db.query(models.Project)
        .join(models.Task)
        .filter(models.Task.assignee_id == current_user.id)
        .all()
    )

    # Combine and remove duplicates
    project_dict = {p.id: p for p in member_projects + task_projects}
    return list(project_dict.values())


# ---------------------------
# GET SINGLE PROJECT
# ---------------------------
@router.get('/{project_id}', response_model=schemas.ProjectDetail)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    project = (
        db.query(models.Project)
        .filter(models.Project.id == project_id)
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail='Project not found')

    if current_user.role.name not in ('admin', 'manager'):
        # Restrict if user not member or assignee
        if not any(m.id == current_user.id for m in project.members) and \
           not any(t.assignee_id == current_user.id for t in project.tasks):
            raise HTTPException(status_code=403, detail='Not permitted')

    # Ensure relationships are loaded
    _ = project.members
    _ = project.tasks

    return project


# ---------------------------
# UPDATE PROJECT
# ---------------------------
@router.put('/{project_id}', response_model=schemas.ProjectOut)
def update_project(
    project_id: int,
    project_in: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role.name not in ('admin', 'manager'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not permitted')

    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')

    if project_in.title:
        project.title = project_in.title
    if project_in.description:
        project.description = project_in.description

    if project_in.member_ids is not None:
        members = db.query(models.User).filter(models.User.id.in_(project_in.member_ids)).all()
        if len(members) != len(set(project_in.member_ids)):
            existing_ids = [m.id for m in members]
            invalid_ids = list(set(project_in.member_ids) - set(existing_ids))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid member IDs: {invalid_ids}"
            )
        project.members = members

    db.commit()
    db.refresh(project)
    return project


# ---------------------------
# DELETE PROJECT
# ---------------------------
@router.delete('/{project_id}')
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role.name != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only admin can delete projects')

    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')

    db.delete(project)
    db.commit()
    return {'ok': True}

# ---------------------------
# TOGGLE PROJECT ARCHIVE
# ---------------------------
@router.put('/{project_id}/archive', response_model=schemas.ProjectOut)
def toggle_archive_project(project_id:int, archive:bool, db:Session=Depends(get_db), current_user:models.User=Depends(get_current_user)):
    if current_user.role.name not in ('admin','manager'):
        raise HTTPException(403, 'Not permitted')
    project = db.query(models.Project).filter_by(id=project_id).first()
    if not project: raise HTTPException(404, 'Project not found')
    project.is_archived = archive
    db.commit(); db.refresh(project)
    return project