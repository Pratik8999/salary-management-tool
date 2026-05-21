"""Tests for GET /api/employees/export.csv

Honors the same filter/sort knobs as the list endpoint, but ignores
limit/offset — the whole filtered result set lands in the CSV.
"""

import csv
import io
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
    email: str,
    first_name: str = "Ada",
    last_name: str = "Lovelace",
    department: str = "Engineering",
    country: str = "UK",
    salary: Decimal | int = 50000,
    is_active: bool = True,
    employment_type: EmploymentType = EmploymentType.FULL_TIME,
    date_joined: date = date(2024, 1, 15),
) -> Employee:
    dept = get_or_create_department(db_session, department)
    emp = Employee(
        first_name=first_name,
        last_name=last_name,
        email=email,
        job_title="Software Engineer",
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


def _parse_csv(body: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(body)))


@pytest.mark.asyncio
async def test_returns_csv_content_type_and_attachment(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="a@example.com")

    response = await client.get("/api/employees/export.csv", headers=_auth(hr))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    disposition = response.headers.get("content-disposition", "")
    assert "attachment" in disposition.lower()
    assert ".csv" in disposition


@pytest.mark.asyncio
async def test_header_row_matches_expected_columns(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="a@example.com")

    response = await client.get("/api/employees/export.csv", headers=_auth(hr))

    reader = csv.reader(io.StringIO(response.text))
    header = next(reader)
    assert header == [
        "id",
        "first_name",
        "last_name",
        "email",
        "job_title",
        "department",
        "country",
        "salary",
        "employment_type",
        "date_joined",
        "is_active",
    ]


@pytest.mark.asyncio
async def test_row_count_matches_filtered_result(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    for i in range(7):
        _make_employee(db_session, hr, email=f"e{i}@example.com")

    response = await client.get("/api/employees/export.csv", headers=_auth(hr))

    rows = _parse_csv(response.text)
    assert len(rows) == 7


@pytest.mark.asyncio
async def test_export_honors_country_filter(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="uk@example.com", country="UK")
    _make_employee(db_session, hr, email="us@example.com", country="US")

    response = await client.get(
        "/api/employees/export.csv?country=UK", headers=_auth(hr)
    )

    rows = _parse_csv(response.text)
    assert [r["email"] for r in rows] == ["uk@example.com"]


@pytest.mark.asyncio
async def test_export_honors_sort(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="lo@example.com", salary=40000)
    _make_employee(db_session, hr, email="hi@example.com", salary=90000)
    _make_employee(db_session, hr, email="mid@example.com", salary=60000)

    response = await client.get(
        "/api/employees/export.csv?sort=salary_desc", headers=_auth(hr)
    )

    rows = _parse_csv(response.text)
    assert [r["email"] for r in rows] == [
        "hi@example.com",
        "mid@example.com",
        "lo@example.com",
    ]


@pytest.mark.asyncio
async def test_export_excludes_inactive_by_default(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="active@example.com", is_active=True)
    _make_employee(db_session, hr, email="gone@example.com", is_active=False)

    response = await client.get("/api/employees/export.csv", headers=_auth(hr))

    rows = _parse_csv(response.text)
    assert [r["email"] for r in rows] == ["active@example.com"]


@pytest.mark.asyncio
async def test_export_includes_inactive_when_asked(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="active@example.com", is_active=True)
    _make_employee(db_session, hr, email="gone@example.com", is_active=False)

    response = await client.get(
        "/api/employees/export.csv?include_inactive=true", headers=_auth(hr)
    )

    rows = _parse_csv(response.text)
    assert sorted(r["email"] for r in rows) == [
        "active@example.com",
        "gone@example.com",
    ]


@pytest.mark.asyncio
async def test_export_ignores_pagination(client, db_session):
    """Export returns the full filtered set, not just one page."""
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    for i in range(120):
        _make_employee(db_session, hr, email=f"e{i}@example.com")

    response = await client.get(
        "/api/employees/export.csv?limit=10&offset=0", headers=_auth(hr)
    )

    rows = _parse_csv(response.text)
    assert len(rows) == 120


@pytest.mark.asyncio
async def test_export_unauthenticated_returns_401(client):
    response = await client.get("/api/employees/export.csv")
    assert response.status_code == 401
