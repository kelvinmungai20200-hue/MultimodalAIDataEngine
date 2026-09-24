import os
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models
from backend.app.auth import create_access_token, hash_password, verify_password
from backend.app.db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.query(models.User).filter(func.lower(models.User.email) == email).first():
        raise HTTPException(status_code=409, detail="Email is already registered")
    user = models.User(
        name=body.name.strip(),
        email=email,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


@router.post("/login")
def login(
    body: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = (
        db.query(models.User)
        .filter(func.lower(models.User.email) == body.username.lower())
        .first()
    )
    if user is None or not user.password_hash or not verify_password(
        body.password, user.password_hash
    ):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


def require_admin_token(request: Request):
    """Dependency that enforces ADMIN_API_TOKEN when set.

    If ADMIN_API_TOKEN env var is not set, this dependency is a no-op (allows access).
    If set, Authorization header must contain the token (supports 'Bearer <token>' or plain token).
    """
    token = os.environ.get("ADMIN_API_TOKEN")
    if not token:
        # no token configured — allow access
        return True

    auth = request.headers.get("Authorization") or ""
    provided = auth.split()[-1] if auth else ""
    if not provided or provided != token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True
