from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin
from app.db.session import get_db
from app.models.user import User
from app.users.schemas import UserCreate, UserRead

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> User:
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    user = User(email=payload.email, role=payload.role, is_active=True)
    user.set_password(payload.password)
    db.add(user)
    db.flush()
    db.refresh(user)
    return user
