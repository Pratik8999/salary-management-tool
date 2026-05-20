import enum

import bcrypt
from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mixins import TimestampMixin
from app.db.session import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    HR = "hr"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    def set_password(self, plaintext: str) -> None:
        self.hashed_password = bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, plaintext: str) -> bool:
        if self.hashed_password is None:
            return False
        return bcrypt.checkpw(plaintext.encode("utf-8"), self.hashed_password.encode("utf-8"))
