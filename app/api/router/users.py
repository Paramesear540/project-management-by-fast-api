from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import models, schemas
from app.db.database import get_db
from app.deps import get_current_user

router = APIRouter()

@router.get('/me', response_model=schemas.UserOut)
def read_own_profile(current_user:models.User=Depends(get_current_user)):
    return current_user

@router.get('/', response_model=list[schemas.UserOut])
def list_users(db:Session=Depends(get_db), current_user:models.User=Depends(get_current_user)):
    if current_user.role.name!='admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not enough privileges')
    return db.query(models.User).all()

# GET user by id (admin)
@router.get('/{user_id}', response_model=schemas.UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user.role or current_user.role.name != 'admin':
        raise HTTPException(status_code=403, detail='Not enough privileges')
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    return user


# PATCH /users/me — update own profile
from pydantic import BaseModel, EmailStr
class UserUpdate(BaseModel):
    username: Optional[str]; email: Optional[EmailStr]

@router.patch('/me', response_model=schemas.UserOut)
def update_own_profile(payload: UserUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if payload.username: current_user.username = payload.username
    if payload.email: current_user.email = payload.email
    db.commit(); db.refresh(current_user)
    return current_user