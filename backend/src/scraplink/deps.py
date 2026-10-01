from collections.abc import Iterator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .env import Env
from .models import Role, User
from .security import decode_access_token


def get_env(request: Request) -> Env:
    return request.app.state.env


def get_db(request: Request) -> Iterator[Session]:
    # Handlers commit explicitly; anything uncommitted is rolled back on close.
    session = request.app.state.sessionmaker()
    try:
        yield session
    finally:
        session.close()


DB = Annotated[Session, Depends(get_db)]
EnvDep = Annotated[Env, Depends(get_env)]

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    db: DB,
    env: EnvDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    unauthorised = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "not signed in", headers={"WWW-Authenticate": "Bearer"}
    )
    if credentials is None:
        raise unauthorised
    try:
        user_id = decode_access_token(credentials.credentials, secret=env.settings.jwt_secret)
    except (jwt.PyJWTError, ValueError):
        raise unauthorised from None
    user = db.get(User, user_id)
    if user is None:
        raise unauthorised
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != Role.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin only")
    return user


Admin = Annotated[User, Depends(require_admin)]
