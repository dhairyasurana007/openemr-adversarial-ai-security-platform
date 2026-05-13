from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from state.db import get_db
from state.models.user import User

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret")
JWT_ALGORITHM = "HS256"

bearer_scheme = HTTPBearer(auto_error=True)


@dataclass
class AuthUser:
    id: UUID
    email: str
    role: str


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthUser:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        sub = payload.get("sub")
        if not sub:
            raise ValueError("missing sub")
        user_id = UUID(sub)
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return AuthUser(id=user.id, email=user.email, role=user.role)


async def require_operator(user: Annotated[AuthUser, Depends(get_current_user)]) -> AuthUser:
    if user.role not in {"operator", "ciso"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operator role required")
    return user


async def require_ciso(user: Annotated[AuthUser, Depends(get_current_user)]) -> AuthUser:
    if user.role != "ciso":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CISO role required")
    return user
