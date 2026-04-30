from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os
from sqlalchemy.orm import Session
from backend import database as db

SECRET_KEY = os.environ.get("SECRET_KEY", "7b547909-3375-8120-4abf-bceb7237b244-saarthi")
ALGORITHM = os.environ.get("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

import logging
logger = logging.getLogger(__name__)

def get_password_hash(password):
    if not password:
        logger.error("Attempted to hash an empty or None password.")
        raise ValueError("Password cannot be empty.")
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db_session: Session = Depends(db.get_db)):
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username:
                user = db_session.query(db.User).filter(db.User.username == username).first()
                if user:
                    return user
        except JWTError:
            pass

    guest_username = "guest_user"
    user = db_session.query(db.User).filter(db.User.username == guest_username).first()
    if not user:
        user = db.User(
            username=guest_username,
            email="guest@saarthi.ai",
            hashed_password=get_password_hash("guest_password") # Dummy password
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    return user

