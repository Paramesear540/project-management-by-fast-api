from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db import models, schemas
from app.db.database import get_db
from app.db.models import User, Role
from passlib.context import CryptContext
from app.security.jwt import create_access_token
from app.db.schemas import UserCreate, Token, UserOut, UserLogin  # make sure Token schema exists

router = APIRouter()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Utility functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Register user endpoint
@router.post("/register", response_model=UserOut)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    # 1. Check if email or username already exists
    existing_user = db.query(User).filter(
        (User.email == user_in.email) | (User.username == user_in.username)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # 2. Get role from role_id
    role = db.query(Role).filter(Role.id == user_in.role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role_id"
        )
    
    # 3. Create the new user
    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        role=role  # assign the relationship
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # 4. Return user info
    return UserOut(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        role_id=new_user.role.id,
        role=new_user.role.name,
        is_active=new_user.is_active
    )

# Login endpoint
@router.post("/token", response_model=Token)
def login_for_access_token(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == user_in.username).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    # Get role name from Role relationship
    role_name = user.role.name if user.role else None

    token_data = {"user_id": user.id, "username": user.username, "role": role_name}
    token = create_access_token(token_data)

    return {"access_token": token, "token_type": "bearer"}

