from pydantic import BaseModel, EmailStr, field_serializer
from typing import Optional, List
from datetime import datetime
import enum

# Optional: keep RoleEnum for role creation convenience
class RoleEnum(str, enum.Enum):
    admin = 'admin'
    manager = 'manager'
    developer = 'developer'

# ------------------ User Schemas ------------------
class UserBase(BaseModel):
    username: str
    email: EmailStr
    role_id: Optional[int]  # optional when returning user info

class UserCreate(UserBase):
    password: str
    role_id: int  # required on create

class RoleOut(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: RoleOut     # <-- changed from str to RoleOut

    class Config:
        orm_mode = True

class UserLogin(BaseModel):
    username: str
    password: str

# ------------------ Project Schemas ------------------
class ProjectBase(BaseModel):
    title: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    member_ids: Optional[List[int]] = []

class ProjectOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    created_at: datetime
    member_ids: List[int]

    class Config:
        from_attributes = True  # ✅ Pydantic v2 equivalent of orm_mode

class ProjectMember(BaseModel):
    id: int
    username: str
    email: str
    role: RoleOut

    class Config:
        orm_mode = True


class TaskMini(BaseModel):
    id: int
    title: str
    status: str
    assignee_id: Optional[int]
    due_date: Optional[datetime]

    class Config:
        orm_mode = True


class ProjectDetail(ProjectOut):
    members: List[ProjectMember]
    tasks: List[TaskMini]

    class Config:
        orm_mode = True


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    member_ids: Optional[List[int]] = None


class ProjectProgress(BaseModel):
    project_id: int
    total_tasks: int
    completed_tasks: int
    completion_percent: float
    
    class Config:
        from_attributes = True  # <-- This enables from_orm in Pydantic v2

# ------------------ Task Schemas ------------------
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None

class TaskCreate(TaskBase):
    assignee_id: Optional[int] = None
    project_id: int

class TaskOut(TaskBase):
    id: int
    status: str
    project_id: int
    assignee_id: Optional[int]
    created_at: datetime
    class Config:
        orm_mode = True

class TaskUpdate(BaseModel):
    title: Optional[str]
    description: Optional[str]
    due_date: Optional[datetime]
    assignee_id: Optional[int]

# ------------------ Comment Schemas ------------------
class CommentCreate(BaseModel):
    content: str
    task_id: int

class AuthorMini(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True  # or orm_mode = True for Pydantic v1

class CommentOut(BaseModel):
    id: int
    content: str
    author: Optional[AuthorMini] = None   # ✅ nested author object
    task_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ------------------ Token Schema ------------------
class Token(BaseModel):
    access_token: str
    token_type: str = 'bearer'
