from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

# auto_error=False so a missing header doesn't 403 before get_optional_user gets a chance
_security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    payload = decode_access_token(credentials.credentials)
    if payload is None or not payload.get("sub"):
        raise unauthorized

    user = db.query(User).filter(User.email == payload["sub"]).first()
    if user is None:
        raise unauthorized
    return user


def get_optional_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    """Returns the authenticated user if a valid Bearer token is present,
    otherwise None — never raises. Used by endpoints that support both guest
    and logged-in flows (e.g. order creation).

    This replaces the previous inline jwt.decode() call in main.py that
    referenced an unimported `jwt` module; the NameError it raised was
    silently swallowed by a bare `except: pass`, so every authenticated
    order was silently downgraded to a guest order and never attributed
    to the user who placed it.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_access_token(token)
    if payload is None or not payload.get("sub"):
        return None
    return db.query(User).filter(User.email == payload["sub"]).first()


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
