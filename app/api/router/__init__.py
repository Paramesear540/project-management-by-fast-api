from fastapi import APIRouter
from . import auth, users, projects, tasks, comments, reporting
router = APIRouter()
router.include_router(auth.router, prefix='/auth', tags=['auth'])
router.include_router(users.router, prefix='/users', tags=['users'])
router.include_router(projects.router, prefix='/projects', tags=['projects'])
router.include_router(tasks.router, prefix='/tasks', tags=['tasks'])
router.include_router(comments.router, prefix='/comments', tags=['comments'])
router.include_router(reporting.router, prefix='/reporting', tags=['reporting'])
