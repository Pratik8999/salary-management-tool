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
    country: str,
    job_title: str,
    salary: Decimal | int,
    department: str = "Engineering",
    is_active: bool = True,
) -> Employee:
    dept = get_or_create_department(db_session, department)
    employee = Employee(
        first_name="Test",
        last_name="Person",
        email=email,
        job_title=job_title,
        country=country,
        salary=salary,
        department_id=dept.id,
        employment_type=EmploymentType.FULL_TIME,
        date_joined=date(2024, 1, 15),
        is_active=is_active,
        created_by_id=hr.id,
    )
    db_session.add(employee)
    db_session.flush()
    db_session.refresh(employee)
    return employee


@pytest.mark.asyncio
async def test_returns_avg_per_job_title_in_country(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(
        db_session, hr, email="e1@example.com", country="UK",
        job_title="Software Engineer", salary=50000,
    )
    _make_employee(
        db_session, hr, email="e2@example.com", country="UK",
        job_title="Software Engineer", salary=70000,
    )
    _make_employee(
        db_session, hr, email="e3@example.com", country="UK",
        job_title="Designer", salary=60000,
    )

    response = await client.get(
        "/api/insights/salary/by-job-title?country=UK", headers=_auth(hr)
    )

    assert response.status_code == 200
    body = response.json()
    by_title = {row["job_title"]: row for row in body}

    assert set(by_title.keys()) == {"Software Engineer", "Designer"}

    se = by_title["Software Engineer"]
    assert se["count"] == 2
    assert Decimal(se["avg"]) == Decimal("60000")

    designer = by_title["Designer"]
    assert designer["count"] == 1
    assert Decimal(designer["avg"]) == Decimal("60000")


@pytest.mark.asyncio
async def test_excludes_other_countries(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(
        db_session, hr, email="uk@example.com", country="UK",
        job_title="Software Engineer", salary=50000,
    )
    _make_employee(
        db_session, hr, email="us@example.com", country="US",
        job_title="Software Engineer", salary=200000,
    )

    response = await client.get(
        "/api/insights/salary/by-job-title?country=UK", headers=_auth(hr)
    )

    body = response.json()
    assert len(body) == 1
    assert Decimal(body[0]["avg"]) == Decimal("50000")


@pytest.mark.asyncio
async def test_country_param_is_case_insensitive(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(
        db_session, hr, email="e@example.com", country="UK",
        job_title="Software Engineer", salary=50000,
    )

    response = await client.get(
        "/api/insights/salary/by-job-title?country=uk", headers=_auth(hr)
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_excludes_inactive_employees(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(
        db_session, hr, email="active@example.com", country="UK",
        job_title="Software Engineer", salary=50000,
    )
    _make_employee(
        db_session, hr, email="inactive@example.com", country="UK",
        job_title="Software Engineer", salary=99999, is_active=False,
    )

    response = await client.get(
        "/api/insights/salary/by-job-title?country=UK", headers=_auth(hr)
    )

    body = response.json()
    assert len(body) == 1
    assert body[0]["count"] == 1
    assert Decimal(body[0]["avg"]) == Decimal("50000")


@pytest.mark.asyncio
async def test_results_ordered_by_job_title(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(
        db_session, hr, email="e1@example.com", country="UK",
        job_title="Software Engineer", salary=1,
    )
    _make_employee(
        db_session, hr, email="e2@example.com", country="UK",
        job_title="Architect", salary=1,
    )
    _make_employee(
        db_session, hr, email="e3@example.com", country="UK",
        job_title="Designer", salary=1,
    )

    response = await client.get(
        "/api/insights/salary/by-job-title?country=UK", headers=_auth(hr)
    )

    titles = [row["job_title"] for row in response.json()]
    assert titles == ["Architect", "Designer", "Software Engineer"]


@pytest.mark.asyncio
async def test_returns_empty_when_no_match(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.get(
        "/api/insights/salary/by-job-title?country=ZZ", headers=_auth(hr)
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_country_param_required(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    response = await client.get(
        "/api/insights/salary/by-job-title", headers=_auth(hr)
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(client):
    response = await client.get("/api/insights/salary/by-job-title?country=UK")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_can_access(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    response = await client.get(
        "/api/insights/salary/by-job-title?country=UK", headers=_auth(admin)
    )
    assert response.status_code == 200
