from typing import Annotated
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token
from app.models import User
from app.repositories import UserRepository

bearer = HTTPBearer(auto_error=False)
Db = Annotated[Session, Depends(get_db)]


def current_user(db: Db, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User:
    if not credentials: raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    try: username = decode_token(credentials.credentials, "access")["sub"]
    except jwt.PyJWTError: raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    user = UserRepository(db).by_username(username)
    if not user or not user.is_active: raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session is no longer active")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_roles(*roles: str):
    def checker(user: CurrentUser) -> User:
        if user.role not in roles: raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permission")
        return user
    return checker
