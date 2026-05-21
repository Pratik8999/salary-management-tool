"""Tests for the new advanced filters and sort options on GET /api/employees."""

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
    email: str,
    job_title: str = "Software Engineer",
    country: str = "UK",
    department: str = "Engineering",
    salary: Decimal | int = 50000,
    employment_type: EmploymentType = EmploymentType.FULL_TIME,
    date_joined: date = date(2024, 1, 15),
    is_active: bool = True,
) -> Employee:
    dept = get_or_create_department(db_session, department)
    emp = Employee(
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
    db_session.add(emp)
    db_session.flush()
    return emp


# --- department_id filter --------------------------------------------------


@pytest.mark.asyncio
async def test_department_id_filter(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    eng = get_or_create_department(db_session, "Engineering")
    sales = get_or_create_department(db_session, "Sales")
    _make_employee(db_session, hr, email="e1@example.com", department="Engineering")
    _make_employee(db_session, hr, email="e2@example.com", department="Engineering")
    _make_employee(db_session, hr, email="s1@example.com", department="Sales")

    response = await client.get(
        f"/api/employees?department_id={sales.id}", headers=_auth(hr)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "s1@example.com"


@pytest.mark.asyncio
async def test_department_id_unknown_returns_empty(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="e1@example.com")

    response = await client.get(
        "/api/employees?department_id=999999", headers=_auth(hr)
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0


# --- job_title filter ------------------------------------------------------


@pytest.mark.asyncio
async def test_job_title_filter_is_partial_and_case_insensitive(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(
        db_session, hr, email="se@example.com", job_title="Software Engineer"
    )
    _make_employee(
        db_session,
        hr,
        email="sse@example.com",
        job_title="Senior Software Engineer",
    )
    _make_employee(
        db_session, hr, email="dm@example.com", job_title="Design Manager"
    )

    response = await client.get(
        "/api/employees?job_title=engineer", headers=_auth(hr)
    )

    assert response.status_code == 200
    emails = sorted(e["email"] for e in response.json()["items"])
    assert emails == ["se@example.com", "sse@example.com"]


# --- employment_type filter ------------------------------------------------


@pytest.mark.asyncio
async def test_employment_type_filter(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(
        db_session,
        hr,
        email="ft@example.com",
        employment_type=EmploymentType.FULL_TIME,
    )
    _make_employee(
        db_session,
        hr,
        email="pt@example.com",
        employment_type=EmploymentType.PART_TIME,
    )
    _make_employee(
        db_session,
        hr,
        email="c@example.com",
        employment_type=EmploymentType.CONTRACT,
    )

    response = await client.get(
        "/api/employees?employment_type=part_time", headers=_auth(hr)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "pt@example.com"


@pytest.mark.asyncio
async def test_unknown_employment_type_rejected_422(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    response = await client.get(
        "/api/employees?employment_type=intern", headers=_auth(hr)
    )
    assert response.status_code == 422


# --- sort -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sort_salary_asc(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="a@example.com", salary=90000)
    _make_employee(db_session, hr, email="b@example.com", salary=40000)
    _make_employee(db_session, hr, email="c@example.com", salary=60000)

    response = await client.get(
        "/api/employees?sort=salary_asc", headers=_auth(hr)
    )

    assert response.status_code == 200
    emails = [e["email"] for e in response.json()["items"]]
    assert emails == ["b@example.com", "c@example.com", "a@example.com"]


@pytest.mark.asyncio
async def test_sort_salary_desc(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="a@example.com", salary=90000)
    _make_employee(db_session, hr, email="b@example.com", salary=40000)
    _make_employee(db_session, hr, email="c@example.com", salary=60000)

    response = await client.get(
        "/api/employees?sort=salary_desc", headers=_auth(hr)
    )

    assert response.status_code == 200
    emails = [e["email"] for e in response.json()["items"]]
    assert emails == ["a@example.com", "c@example.com", "b@example.com"]


@pytest.mark.asyncio
async def test_sort_date_joined_desc(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(
        db_session, hr, email="old@example.com", date_joined=date(2020, 1, 1)
    )
    _make_employee(
        db_session, hr, email="new@example.com", date_joined=date(2025, 1, 1)
    )
    _make_employee(
        db_session, hr, email="mid@example.com", date_joined=date(2022, 1, 1)
    )

    response = await client.get(
        "/api/employees?sort=date_joined_desc", headers=_auth(hr)
    )

    assert response.status_code == 200
    emails = [e["email"] for e in response.json()["items"]]
    assert emails == ["new@example.com", "mid@example.com", "old@example.com"]


@pytest.mark.asyncio
async def test_sort_name_asc(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(
        db_session,
        hr,
        first_name="Zara",
        last_name="Khan",
        email="z@example.com",
    )
    _make_employee(
        db_session,
        hr,
        first_name="Ada",
        last_name="Lovelace",
        email="a@example.com",
    )
    _make_employee(
        db_session,
        hr,
        first_name="Mira",
        last_name="Singh",
        email="m@example.com",
    )

    response = await client.get(
        "/api/employees?sort=name_asc", headers=_auth(hr)
    )

    assert response.status_code == 200
    emails = [e["email"] for e in response.json()["items"]]
    assert emails == ["a@example.com", "m@example.com", "z@example.com"]


@pytest.mark.asyncio
async def test_unknown_sort_value_rejected_422(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    response = await client.get(
        "/api/employees?sort=salary_oops", headers=_auth(hr)
    )
    assert response.status_code == 422


# --- countries list --------------------------------------------------------


@pytest.mark.asyncio
async def test_countries_endpoint_returns_distinct_sorted(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="a@example.com", country="India")
    _make_employee(db_session, hr, email="b@example.com", country="UK")
    _make_employee(db_session, hr, email="c@example.com", country="India")
    _make_employee(db_session, hr, email="d@example.com", country="Canada")

    response = await client.get("/api/employees/countries", headers=_auth(hr))

    assert response.status_code == 200
    assert response.json() == ["Canada", "India", "UK"]


@pytest.mark.asyncio
async def test_countries_endpoint_excludes_inactive(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="a@example.com", country="India")
    _make_employee(
        db_session, hr, email="b@example.com", country="Atlantis", is_active=False
    )

    response = await client.get("/api/employees/countries", headers=_auth(hr))

    assert response.status_code == 200
    assert response.json() == ["India"]


@pytest.mark.asyncio
async def test_countries_unauthenticated_returns_401(client):
    response = await client.get("/api/employees/countries")
    assert response.status_code == 401
