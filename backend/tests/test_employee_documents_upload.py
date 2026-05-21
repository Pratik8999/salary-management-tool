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
from app.models.employee_document import DocumentType, EmployeeDocument
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


def _make_employee(db_session, hr: User) -> Employee:
    dept = get_or_create_department(db_session, "Engineering")
    employee = Employee(
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
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
    """Client with the storage root overridden to a tmp dir."""
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


@pytest.mark.asyncio
async def test_hr_can_upload_document(storage_client, db_session):
    ac, storage_root = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await ac.post(
        f"/api/employees/{employee.id}/documents",
        headers=_auth(hr),
        data={"doc_type": "offer_letter"},
        files={"file": ("offer.pdf", b"%PDF-1.4 fake pdf bytes", "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["employee_id"] == employee.id
    assert body["uploaded_by_id"] == hr.id
    assert body["doc_type"] == "offer_letter"
    assert body["file_name"] == "offer.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["size_bytes"] == len(b"%PDF-1.4 fake pdf bytes")
    assert "id" in body
    assert "storage_path" in body
    assert "uploaded_at" in body


@pytest.mark.asyncio
async def test_upload_persists_file_on_disk(storage_client, db_session):
    ac, storage_root = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    payload = b"hello-world-bytes"
    response = await ac.post(
        f"/api/employees/{employee.id}/documents",
        headers=_auth(hr),
        data={"doc_type": "id_proof"},
        files={"file": ("id.pdf", payload, "application/pdf")},
    )

    assert response.status_code == 201
    storage_path = response.json()["storage_path"]
    full_path = storage_root / storage_path
    assert full_path.exists()
    assert full_path.read_bytes() == payload


@pytest.mark.asyncio
async def test_upload_creates_db_row(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await ac.post(
        f"/api/employees/{employee.id}/documents",
        headers=_auth(hr),
        data={"doc_type": "contract"},
        files={"file": ("contract.pdf", b"x" * 100, "application/pdf")},
    )

    assert response.status_code == 201
    doc_id = response.json()["id"]
    doc = db_session.get(EmployeeDocument, doc_id)
    assert doc is not None
    assert doc.employee_id == employee.id
    assert doc.doc_type is DocumentType.CONTRACT
    assert doc.size_bytes == 100


@pytest.mark.asyncio
async def test_admin_can_upload_document(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)

    response = await ac.post(
        f"/api/employees/{employee.id}/documents",
        headers=_auth(admin),
        data={"doc_type": "other"},
        files={"file": ("note.pdf", b"abc", "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["uploaded_by_id"] == admin.id


@pytest.mark.asyncio
async def test_multiple_uploads_create_separate_rows(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    r1 = await ac.post(
        f"/api/employees/{employee.id}/documents",
        headers=_auth(hr),
        data={"doc_type": "id_proof"},
        files={"file": ("a.pdf", b"a", "application/pdf")},
    )
    r2 = await ac.post(
        f"/api/employees/{employee.id}/documents",
        headers=_auth(hr),
        data={"doc_type": "id_proof"},
        files={"file": ("b.pdf", b"b", "application/pdf")},
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] != r2.json()["id"]
    assert r1.json()["storage_path"] != r2.json()["storage_path"]


@pytest.mark.asyncio
async def test_rejects_unsupported_content_type(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await ac.post(
        f"/api/employees/{employee.id}/documents",
        headers=_auth(hr),
        data={"doc_type": "other"},
        files={
            "file": (
                "evil.exe",
                b"MZ\x90\x00",
                "application/x-msdownload",
            )
        },
    )

    assert response.status_code == 415


@pytest.mark.asyncio
async def test_rejects_file_over_size_limit(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    # 5 MB + 1 byte over the limit
    huge = b"x" * (5 * 1024 * 1024 + 1)
    response = await ac.post(
        f"/api/employees/{employee.id}/documents",
        headers=_auth(hr),
        data={"doc_type": "other"},
        files={"file": ("big.pdf", huge, "application/pdf")},
    )

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_invalid_doc_type_returns_422(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await ac.post(
        f"/api/employees/{employee.id}/documents",
        headers=_auth(hr),
        data={"doc_type": "payslip"},
        files={"file": ("a.pdf", b"a", "application/pdf")},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_returns_404_when_employee_not_found(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await ac.post(
        "/api/employees/999999/documents",
        headers=_auth(hr),
        data={"doc_type": "id_proof"},
        files={"file": ("a.pdf", b"a", "application/pdf")},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await ac.post(
        f"/api/employees/{employee.id}/documents",
        data={"doc_type": "id_proof"},
        files={"file": ("a.pdf", b"a", "application/pdf")},
    )

    assert response.status_code == 401
