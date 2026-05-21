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
from app.models.employee_document import EmployeeDocument
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


async def _upload(ac, employee_id, hr, *, doc_type="id_proof", file_name="x.pdf",
                  payload=b"x"):
    return await ac.post(
        f"/api/employees/{employee_id}/documents",
        headers=_auth(hr),
        data={"doc_type": doc_type},
        files={"file": (file_name, payload, "application/pdf")},
    )


@pytest.mark.asyncio
async def test_hr_can_delete_document(storage_client, db_session):
    ac, storage_root = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)
    up = await _upload(ac, employee.id, hr, payload=b"some-bytes")
    doc_id = up.json()["id"]
    storage_path = up.json()["storage_path"]
    assert (storage_root / storage_path).exists()

    response = await ac.delete(
        f"/api/employees/{employee.id}/documents/{doc_id}",
        headers=_auth(hr),
    )

    assert response.status_code == 204
    assert response.content == b""
    # DB row gone
    db_session.expire_all()
    assert db_session.get(EmployeeDocument, doc_id) is None
    # File gone from disk
    assert not (storage_root / storage_path).exists()


@pytest.mark.asyncio
async def test_admin_can_delete_document(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    employee = _make_employee(db_session, hr)
    up = await _upload(ac, employee.id, hr)
    doc_id = up.json()["id"]

    response = await ac.delete(
        f"/api/employees/{employee.id}/documents/{doc_id}",
        headers=_auth(admin),
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_idempotent_when_file_already_gone(storage_client, db_session):
    """If the file is missing on disk but the DB row exists, deletion still
    succeeds — we want the row to go away regardless."""
    ac, storage_root = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)
    up = await _upload(ac, employee.id, hr)
    doc_id = up.json()["id"]
    (storage_root / up.json()["storage_path"]).unlink()

    response = await ac.delete(
        f"/api/employees/{employee.id}/documents/{doc_id}",
        headers=_auth(hr),
    )

    assert response.status_code == 204
    db_session.expire_all()
    assert db_session.get(EmployeeDocument, doc_id) is None


@pytest.mark.asyncio
async def test_delete_404_when_document_not_found(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await ac.delete(
        f"/api/employees/{employee.id}/documents/999999",
        headers=_auth(hr),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_404_when_doc_belongs_to_other_employee(
    storage_client, db_session
):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    emp_a = _make_employee(db_session, hr, email="a@example.com")
    emp_b = _make_employee(db_session, hr, email="b@example.com")
    up = await _upload(ac, emp_a.id, hr)
    doc_id = up.json()["id"]

    response = await ac.delete(
        f"/api/employees/{emp_b.id}/documents/{doc_id}",
        headers=_auth(hr),
    )

    assert response.status_code == 404
    # Doc still there
    db_session.expire_all()
    assert db_session.get(EmployeeDocument, doc_id) is not None


@pytest.mark.asyncio
async def test_delete_404_when_employee_not_found(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await ac.delete(
        "/api/employees/999999/documents/1",
        headers=_auth(hr),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_unauthenticated_returns_401(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)
    up = await _upload(ac, employee.id, hr)
    doc_id = up.json()["id"]

    response = await ac.delete(f"/api/employees/{employee.id}/documents/{doc_id}")

    assert response.status_code == 401
