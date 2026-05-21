from datetime import date

import pytest

from app.auth.jwt_handler import create_access_token
from app.departments.service import get_or_create_department
from app.models.employee import Employee
from app.models.user import User, UserRole


def _seeded_user(db_session, *, email: str, role: UserRole, is_active: bool = True) -> User:
    user = User(email=email, role=role, is_active=is_active)
    user.set_password("any-password")
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)
    return user


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _payload(**overrides) -> dict:
    base = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "job_title": "Software Engineer",
        "country": "UK",
        "salary": "50000.00",
        "department": "Engineering",
        "employment_type": "full_time",
        "date_joined": "2024-01-15",
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_hr_can_create_employee(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.post("/api/employees", headers=_auth(hr), json=_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ada@example.com"
    assert body["full_name"] == "Ada Lovelace"
    assert body["employment_type"] == "full_time"
    assert body["is_active"] is True
    assert body["created_by_id"] == hr.id
    assert "id" in body


@pytest.mark.asyncio
async def test_create_persists_to_db(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.post("/api/employees", headers=_auth(hr), json=_payload())
    assert response.status_code == 201

    employee = db_session.query(Employee).filter_by(email="ada@example.com").one()
    assert employee.first_name == "Ada"
    assert employee.created_by_id == hr.id
    assert employee.date_joined == date(2024, 1, 15)


@pytest.mark.asyncio
async def test_duplicate_email_returns_409(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    qa_dept = get_or_create_department(db_session, "QA")
    db_session.add(
        Employee(
            first_name="Existing",
            last_name="Person",
            email="taken@example.com",
            job_title="QA",
            country="IN",
            salary=40000,
            department_id=qa_dept.id,
            employment_type="full_time",
            date_joined=date(2023, 1, 1),
            created_by_id=hr.id,
        )
    )
    db_session.flush()

    response = await client.post(
        "/api/employees", headers=_auth(hr), json=_payload(email="taken@example.com")
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_admin_cannot_create_employee(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)

    response = await client.post("/api/employees", headers=_auth(admin), json=_payload())

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401(client):
    response = await client.post("/api/employees", json=_payload())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_payload_returns_422(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.post(
        "/api/employees",
        headers=_auth(hr),
        json=_payload(salary="-100", email="not-an-email"),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_future_date_joined_returns_422(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.post(
        "/api/employees",
        headers=_auth(hr),
        json=_payload(date_joined="2099-01-01"),
    )

    assert response.status_code == 422
