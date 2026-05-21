import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.mixins import TimestampMixin
from app.db.session import Base
from app.models.department import Department
from app.models.user import User


class EmploymentType(str, enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"


class Employee(Base, TimestampMixin):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(150), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False
    )
    employment_type: Mapped[EmploymentType] = mapped_column(
        Enum(
            EmploymentType,
            name="employment_type",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    date_joined: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    created_by: Mapped[User] = relationship(User, lazy="joined")
    department_ref: Mapped[Department] = relationship(Department, lazy="joined")

    __table_args__ = (
        Index("ix_employees_email", "email", unique=True),
        Index("ix_employees_country", "country"),
        Index("ix_employees_department_id", "department_id"),
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name.strip()} {self.last_name.strip()}"

    @property
    def department(self) -> str:
        return self.department_ref.name

    @property
    def currency(self) -> str | None:
        # Imported lazily to avoid pulling reference data into the
        # SQLAlchemy import graph; the catalog is plain Python and cheap
        # to look up per-row.
        from app.reference.countries import currency_for

        return currency_for(self.country)
