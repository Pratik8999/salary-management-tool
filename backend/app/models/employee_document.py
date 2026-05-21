import enum

from sqlalchemy import Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.mixins import TimestampMixin
from app.db.session import Base
from app.models.employee import Employee
from app.models.user import User


class DocumentType(str, enum.Enum):
    ID_PROOF = "id_proof"
    OFFER_LETTER = "offer_letter"
    CONTRACT = "contract"
    OTHER = "other"


class EmployeeDocument(Base, TimestampMixin):
    __tablename__ = "employee_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    uploaded_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    doc_type: Mapped[DocumentType] = mapped_column(
        Enum(
            DocumentType,
            name="document_type",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)

    employee: Mapped[Employee] = relationship(Employee, lazy="joined")
    uploaded_by: Mapped[User] = relationship(User, lazy="joined")

    __table_args__ = (
        Index("ix_employee_documents_employee_id", "employee_id"),
    )
