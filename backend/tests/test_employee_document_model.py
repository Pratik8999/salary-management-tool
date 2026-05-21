from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.departments.service import get_or_create_department
from app.models.employee import Employee, EmploymentType
from app.models.employee_document import DocumentType, EmployeeDocument
from app.models.user import User, UserRole


def _hr(db_session) -> User:
    user = User(email="hr@example.com", role=UserRole.HR)
    user.set_password("any-password")
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)
    return user


def _employee(db_session, hr: User, *, email: str = "ada@example.com") -> Employee:
    dept = get_or_create_department(db_session, "Engineering")
    employee = Employee(
        first_name="Ada",
        last_name="Lovelace",
        email=email,
        job_title="Software Engineer",
        country="UK",
        salary=Decimal("50000.00"),
        department_id=dept.id,
        employment_type=EmploymentType.FULL_TIME,
        date_joined=date(2024, 1, 15),
        created_by_id=hr.id,
    )
    db_session.add(employee)
    db_session.flush()
    db_session.refresh(employee)
    return employee


def _doc_kwargs(**overrides) -> dict:
    base = dict(
        doc_type=DocumentType.OFFER_LETTER,
        file_name="offer.pdf",
        content_type="application/pdf",
        size_bytes=2048,
        storage_path="documents/1/offer.pdf",
    )
    base.update(overrides)
    return base


def test_document_type_enum_values():
    assert DocumentType("id_proof") is DocumentType.ID_PROOF
    assert DocumentType("offer_letter") is DocumentType.OFFER_LETTER
    assert DocumentType("contract") is DocumentType.CONTRACT
    assert DocumentType("other") is DocumentType.OTHER


def test_document_type_rejects_unknown():
    with pytest.raises(ValueError):
        DocumentType("payslip")


def test_persists_with_required_fields(db_session):
    hr = _hr(db_session)
    employee = _employee(db_session, hr)

    doc = EmployeeDocument(
        employee_id=employee.id,
        uploaded_by_id=hr.id,
        **_doc_kwargs(),
    )
    db_session.add(doc)
    db_session.flush()
    db_session.refresh(doc)

    assert doc.id is not None
    assert doc.employee_id == employee.id
    assert doc.uploaded_by_id == hr.id
    assert doc.doc_type is DocumentType.OFFER_LETTER
    assert doc.file_name == "offer.pdf"
    assert doc.content_type == "application/pdf"
    assert doc.size_bytes == 2048
    assert doc.storage_path == "documents/1/offer.pdf"
    assert doc.created_at is not None
    assert doc.updated_at is not None


def test_employee_relationship_resolves(db_session):
    hr = _hr(db_session)
    employee = _employee(db_session, hr)

    doc = EmployeeDocument(
        employee_id=employee.id, uploaded_by_id=hr.id, **_doc_kwargs()
    )
    db_session.add(doc)
    db_session.flush()
    db_session.refresh(doc)

    assert doc.employee.id == employee.id
    assert doc.uploaded_by.email == "hr@example.com"


def test_employee_id_is_required(db_session):
    hr = _hr(db_session)
    db_session.add(
        EmployeeDocument(uploaded_by_id=hr.id, **_doc_kwargs())
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_uploaded_by_id_is_required(db_session):
    hr = _hr(db_session)
    employee = _employee(db_session, hr)
    db_session.add(
        EmployeeDocument(employee_id=employee.id, **_doc_kwargs())
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_documents_deleted_when_employee_deleted(db_session):
    hr = _hr(db_session)
    employee = _employee(db_session, hr)
    doc = EmployeeDocument(
        employee_id=employee.id, uploaded_by_id=hr.id, **_doc_kwargs()
    )
    db_session.add(doc)
    db_session.flush()
    doc_id = doc.id

    db_session.delete(employee)
    db_session.flush()

    remaining = db_session.execute(
        select(EmployeeDocument).where(EmployeeDocument.id == doc_id)
    ).scalar_one_or_none()
    assert remaining is None
