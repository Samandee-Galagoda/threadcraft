from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import ProfileUpdate, Token, UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=Token)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    new_user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(data={"sub": new_user.email})
    return {"access_token": token, "user": new_user}


@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email address or password.",
        )
    token = create_access_token(data={"sub": user.email})
    return {"access_token": token, "user": user}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Edit your own name, email or password.

    Not admin-only: an administrator editing their profile and a customer
    editing theirs are the same operation, and giving admins a separate path
    would mean two places to keep the credential rules correct.
    """
    changing_credentials = payload.email is not None or payload.new_password is not None
    if changing_credentials:
        # Re-authenticate before either credential moves. Without this, anyone
        # holding a stolen token could change the address and password and lock
        # the real owner out of their own account.
        if not payload.current_password or not verify_password(
            payload.current_password, current_user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Enter your current password to change your email address or password.",
            )

    if payload.email and payload.email != current_user.email:
        taken = db.query(User).filter(User.email == payload.email, User.id != current_user.id).first()
        if taken:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Another account already uses that email address.",
            )
        current_user.email = payload.email

    if payload.first_name is not None:
        current_user.first_name = payload.first_name
    if payload.last_name is not None:
        current_user.last_name = payload.last_name
    if payload.new_password:
        current_user.password_hash = get_password_hash(payload.new_password)

    db.commit()
    db.refresh(current_user)
    return current_user
