from sqlalchemy import Boolean, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mixins import TimestampMixin
from app.db.session import Base


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    __table_args__ = (
        Index(
            "ix_departments_name_lower",
            func.lower(name),
            unique=True,
        ),
    )
