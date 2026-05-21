from datetime import date
from decimal import Decimal

import pytest

from app.auth.jwt_handler import create_access_token
from app.departments.service import get_or_create_department
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
    db_session,
    hr: User,
    *,
    first_name: str = "Ada",
    last_name: str = "Lovelace",
    email: str = "ada@example.com",
    job_title: str = "Software Engineer",
    country: str = "UK",
    department: str = "Engineering",
    salary: Decimal | int = 50000,
    employment_type: EmploymentType = EmploymentType.FULL_TIME,
    date_joined: date = date(2024, 1, 15),
    is_active: bool = True,
) -> Employee:
    dept = get_or_create_department(db_session, department)
    employee = Employee(
        first_name=first_name,
        last_name=last_name,
        email=email,
        job_title=job_title,
        country=country,
        salary=salary,
        department_id=dept.id,
        employment_type=employment_type,
        date_joined=date_joined,
        is_active=is_active,
        created_by_id=hr.id,
    )
    db_session.add(employee)
    db_session.flush()
    return employee


@pytest.mark.asyncio
async def test_returns_paginated_envelope(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    for i in range(3):
        _make_employee(db_session, hr, email=f"e{i}@example.com")

    response = await client.get("/api/employees", headers=_auth(hr))

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"items", "total", "limit", "offset"}
    assert body["total"] == 3
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert len(body["items"]) == 3


@pytest.mark.asyncio
async def test_pagination_respects_limit_and_offset(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    for i in range(5):
        _make_employee(db_session, hr, email=f"e{i}@example.com")

    response = await client.get(
        "/api/employees?limit=2&offset=2", headers=_auth(hr)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert body["limit"] == 2
    assert body["offset"] == 2
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_active_by_default_hides_inactive(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="active@example.com", is_active=True)
    _make_employee(db_session, hr, email="inactive@example.com", is_active=False)

    response = await client.get("/api/employees", headers=_auth(hr))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "active@example.com"


@pytest.mark.asyncio
async def test_include_inactive_returns_everyone(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="active@example.com", is_active=True)
    _make_employee(db_session, hr, email="inactive@example.com", is_active=False)

    response = await client.get(
        "/api/employees?include_inactive=true", headers=_auth(hr)
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2


@pytest.mark.asyncio
async def test_q_matches_first_name_last_name_email_and_job_title(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(
        db_session, hr, first_name="Ada", last_name="Lovelace", email="ada@example.com"
    )
    _make_employee(
        db_session,
        hr,
        first_name="Grace",
        last_name="Hopper",
        email="grace@example.com",
    )
    _make_employee(
        db_session,
        hr,
        first_name="Bob",
        last_name="Smith",
        email="bob@example.com",
        job_title="Lovelace Specialist",
    )

    response = await client.get("/api/employees?q=lovelace", headers=_auth(hr))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    emails = {item["email"] for item in body["items"]}
    assert emails == {"ada@example.com", "bob@example.com"}


@pytest.mark.asyncio
async def test_q_is_case_insensitive(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, first_name="Ada", email="ada@example.com")

    response = await client.get("/api/employees?q=ADA", headers=_auth(hr))

    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_department_filter(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(
        db_session, hr, email="eng@example.com", department="Engineering"
    )
    _make_employee(
        db_session, hr, email="sales@example.com", department="Sales"
    )

    response = await client.get(
        "/api/employees?department=Sales", headers=_auth(hr)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "sales@example.com"


@pytest.mark.asyncio
async def test_q_and_department_combine(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(
        db_session,
        hr,
        first_name="Ada",
        email="ada-eng@example.com",
        department="Engineering",
    )
    _make_employee(
        db_session,
        hr,
        first_name="Ada",
        last_name="Other",
        email="ada-sales@example.com",
        department="Sales",
    )

    response = await client.get(
        "/api/employees?q=Ada&department=Engineering", headers=_auth(hr)
    )

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "ada-eng@example.com"


@pytest.mark.asyncio
async def test_admin_cannot_list_employees(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    response = await client.get("/api/employees", headers=_auth(admin))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(client):
    response = await client.get("/api/employees")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_limit_bounds_enforced(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    response = await client.get("/api/employees?limit=0", headers=_auth(hr))
    assert response.status_code == 422

    response = await client.get("/api/employees?limit=500", headers=_auth(hr))
    assert response.status_code == 422


# --- GET /employees/departments ---


@pytest.mark.asyncio
async def test_departments_returns_distinct_sorted_list(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="e1@example.com", department="Engineering")
    _make_employee(db_session, hr, email="e2@example.com", department="Engineering")
    _make_employee(db_session, hr, email="e3@example.com", department="Sales")
    _make_employee(db_session, hr, email="e4@example.com", department="IT")

    response = await client.get("/api/employees/departments", headers=_auth(hr))

    assert response.status_code == 200
    assert response.json() == ["Engineering", "IT", "Sales"]


@pytest.mark.asyncio
async def test_departments_excludes_inactive_employees(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="a@example.com", department="Engineering")
    _make_employee(
        db_session, hr, email="b@example.com", department="HR", is_active=False
    )

    response = await client.get("/api/employees/departments", headers=_auth(hr))

    assert response.status_code == 200
    assert response.json() == ["Engineering"]


@pytest.mark.asyncio
async def test_departments_returns_empty_when_no_employees(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.get("/api/employees/departments", headers=_auth(hr))

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_departments_is_hr_only(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    response = await client.get("/api/employees/departments", headers=_auth(admin))
    assert response.status_code == 403
