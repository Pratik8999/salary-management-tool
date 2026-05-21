from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.auth.jwt_handler import create_access_token
from app.departments.service import get_or_create_department
from app.documents.dependencies import get_storage_root
from app.main import app
from app.models.employee import Employee, EmploymentType
from app.models.user import User, UserRole


def _seeded_user(db_session, *, email: str, role: UserRole) -> User:
    user = User(email=email, role=role)
    user.set_password("any-password")
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)
    return user


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _make_employee(
    db_session, hr: User, *, email: str = "ada@example.com"
) -> Employee:
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


@pytest_asyncio.fixture
async def storage_client(db_session, tmp_path):
    from app.db.session import get_db

    def override_get_db():
        yield db_session

    def override_storage_root() -> Path:
        return tmp_path

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_root] = override_storage_root
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, tmp_path
    app.dependency_overrides.clear()


async def _upload(ac, employee_id, hr, *, doc_type, file_name, payload):
    return await ac.post(
        f"/api/employees/{employee_id}/documents",
        headers=_auth(hr),
        data={"doc_type": doc_type},
        files={"file": (file_name, payload, "application/pdf")},
    )


@pytest.mark.asyncio
async def test_hr_can_download_document(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)
    payload = b"%PDF-1.4 fake bytes for download"
    up = await _upload(
        ac, employee.id, hr, doc_type="offer_letter", file_name="offer.pdf",
        payload=payload,
    )
    assert up.status_code == 201
    doc_id = up.json()["id"]

    response = await ac.get(
        f"/api/employees/{employee.id}/documents/{doc_id}/download",
        headers=_auth(hr),
    )

    assert response.status_code == 200
    assert response.content == payload
    assert response.headers["content-type"].startswith("application/pdf")
    disposition = response.headers.get("content-disposition", "")
    assert "attachment" in disposition.lower()
    assert "offer.pdf" in disposition


@pytest.mark.asyncio
async def test_admin_can_download_document(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    employee = _make_employee(db_session, hr)
    up = await _upload(
        ac, employee.id, hr, doc_type="contract", file_name="c.pdf",
        payload=b"contract-bytes",
    )
    doc_id = up.json()["id"]

    response = await ac.get(
        f"/api/employees/{employee.id}/documents/{doc_id}/download",
        headers=_auth(admin),
    )

    assert response.status_code == 200
    assert response.content == b"contract-bytes"


@pytest.mark.asyncio
async def test_download_404_when_document_not_found(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await ac.get(
        f"/api/employees/{employee.id}/documents/999999/download",
        headers=_auth(hr),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_download_404_when_doc_belongs_to_other_employee(
    storage_client, db_session
):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    emp_a = _make_employee(db_session, hr, email="a@example.com")
    emp_b = _make_employee(db_session, hr, email="b@example.com")
    up = await _upload(
        ac, emp_a.id, hr, doc_type="id_proof", file_name="a.pdf", payload=b"a",
    )
    doc_id = up.json()["id"]

    response = await ac.get(
        f"/api/employees/{emp_b.id}/documents/{doc_id}/download",
        headers=_auth(hr),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_download_404_when_employee_not_found(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await ac.get(
        "/api/employees/999999/documents/1/download",
        headers=_auth(hr),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_download_500_when_file_missing_on_disk(storage_client, db_session):
    ac, storage_root = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)
    up = await _upload(
        ac, employee.id, hr, doc_type="id_proof", file_name="x.pdf", payload=b"x",
    )
    doc_id = up.json()["id"]
    # Simulate a disk-level loss: remove the file but keep the DB row.
    (storage_root / up.json()["storage_path"]).unlink()

    response = await ac.get(
        f"/api/employees/{employee.id}/documents/{doc_id}/download",
        headers=_auth(hr),
    )

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_download_unauthenticated_returns_401(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)
    up = await _upload(
        ac, employee.id, hr, doc_type="id_proof", file_name="x.pdf", payload=b"x",
    )
    doc_id = up.json()["id"]

    response = await ac.get(
        f"/api/employees/{employee.id}/documents/{doc_id}/download",
    )

    assert response.status_code == 401
