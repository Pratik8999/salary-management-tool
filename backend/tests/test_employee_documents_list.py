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


async def _upload(ac, employee_id, hr, *, doc_type, file_name, payload=b"x"):
    return await ac.post(
        f"/api/employees/{employee_id}/documents",
        headers=_auth(hr),
        data={"doc_type": doc_type},
        files={"file": (file_name, payload, "application/pdf")},
    )


@pytest.mark.asyncio
async def test_hr_can_list_employee_documents(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    await _upload(ac, employee.id, hr, doc_type="offer_letter", file_name="offer.pdf")
    await _upload(ac, employee.id, hr, doc_type="contract", file_name="contract.pdf")

    response = await ac.get(
        f"/api/employees/{employee.id}/documents",
        headers=_auth(hr),
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 2
    file_names = {d["file_name"] for d in body}
    assert file_names == {"offer.pdf", "contract.pdf"}
    for item in body:
        assert item["employee_id"] == employee.id
        assert "id" in item
        assert "doc_type" in item
        assert "content_type" in item
        assert "size_bytes" in item
        assert "uploaded_at" in item
        assert "storage_path" in item


@pytest.mark.asyncio
async def test_list_returns_newest_first(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    r1 = await _upload(ac, employee.id, hr, doc_type="id_proof", file_name="first.pdf")
    r2 = await _upload(
        ac, employee.id, hr, doc_type="id_proof", file_name="second.pdf"
    )
    assert r1.status_code == 201 and r2.status_code == 201

    response = await ac.get(
        f"/api/employees/{employee.id}/documents",
        headers=_auth(hr),
    )

    assert response.status_code == 200
    body = response.json()
    assert [d["id"] for d in body] == [r2.json()["id"], r1.json()["id"]]


@pytest.mark.asyncio
async def test_list_returns_empty_when_no_documents(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await ac.get(
        f"/api/employees/{employee.id}/documents",
        headers=_auth(hr),
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_scoped_to_requested_employee(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    emp_a = _make_employee(db_session, hr, email="a@example.com")
    emp_b = _make_employee(db_session, hr, email="b@example.com")

    await _upload(ac, emp_a.id, hr, doc_type="id_proof", file_name="a.pdf")
    await _upload(ac, emp_b.id, hr, doc_type="id_proof", file_name="b1.pdf")
    await _upload(ac, emp_b.id, hr, doc_type="contract", file_name="b2.pdf")

    response = await ac.get(
        f"/api/employees/{emp_b.id}/documents",
        headers=_auth(hr),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {d["file_name"] for d in body} == {"b1.pdf", "b2.pdf"}
    assert all(d["employee_id"] == emp_b.id for d in body)


@pytest.mark.asyncio
async def test_admin_can_list_documents(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    employee = _make_employee(db_session, hr)
    await _upload(ac, employee.id, hr, doc_type="other", file_name="x.pdf")

    response = await ac.get(
        f"/api/employees/{employee.id}/documents",
        headers=_auth(admin),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_list_returns_404_when_employee_not_found(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await ac.get(
        "/api/employees/999999/documents",
        headers=_auth(hr),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_unauthenticated_returns_401(storage_client, db_session):
    ac, _ = storage_client
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await ac.get(f"/api/employees/{employee.id}/documents")

    assert response.status_code == 401
