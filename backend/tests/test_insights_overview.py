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
    department: str = "Engineering",
    job_title: str = "Software Engineer",
    salary: Decimal | int = 50000,
    is_active: bool = True,
) -> Employee:
    dept = get_or_create_department(db_session, department)
    emp = Employee(
        first_name="X",
        last_name="Y",
        email=email,
        job_title=job_title,
        country="UK",
        salary=salary,
        department_id=dept.id,
        employment_type=EmploymentType.FULL_TIME,
        date_joined=date(2024, 1, 15),
        is_active=is_active,
        created_by_id=hr.id,
    )
    db_session.add(emp)
    db_session.flush()
    return emp


@pytest.mark.asyncio
async def test_overview_reports_headcount_and_avg_salary(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="a@example.com", salary=40000)
    _make_employee(db_session, hr, email="b@example.com", salary=60000)
    _make_employee(db_session, hr, email="c@example.com", salary=80000)

    response = await client.get("/api/insights/overview", headers=_auth(hr))

    assert response.status_code == 200
    body = response.json()
    assert body["total_headcount"] == 3
    assert Decimal(body["avg_salary"]) == Decimal("60000")


@pytest.mark.asyncio
async def test_overview_excludes_inactive_employees_everywhere(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="a@example.com", salary=50000)
    _make_employee(
        db_session, hr, email="gone@example.com", salary=999999, is_active=False
    )

    response = await client.get("/api/insights/overview", headers=_auth(hr))

    body = response.json()
    assert body["total_headcount"] == 1
    assert Decimal(body["avg_salary"]) == Decimal("50000")


@pytest.mark.asyncio
async def test_overview_handles_zero_employees(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.get("/api/insights/overview", headers=_auth(hr))

    assert response.status_code == 200
    body = response.json()
    assert body["total_headcount"] == 0
    assert body["avg_salary"] is None
    assert body["headcount_by_department"] == []
    assert body["top_paid_job_titles"] == []


@pytest.mark.asyncio
async def test_headcount_by_department_groups_correctly(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="e1@example.com", department="Engineering")
    _make_employee(db_session, hr, email="e2@example.com", department="Engineering")
    _make_employee(db_session, hr, email="s1@example.com", department="Sales")

    response = await client.get("/api/insights/overview", headers=_auth(hr))

    body = response.json()
    by_name = {row["department"]: row["count"] for row in body["headcount_by_department"]}
    assert by_name == {"Engineering": 2, "Sales": 1}


@pytest.mark.asyncio
async def test_top_paid_job_titles_are_top_5_by_avg_salary(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    titles = [
        ("Intern", 30000),
        ("Junior Engineer", 50000),
        ("Engineer", 80000),
        ("Senior Engineer", 120000),
        ("Staff Engineer", 160000),
        ("Principal Engineer", 200000),
        ("Director", 240000),
    ]
    for i, (title, salary) in enumerate(titles):
        _make_employee(
            db_session, hr, email=f"e{i}@example.com", job_title=title, salary=salary
        )

    response = await client.get("/api/insights/overview", headers=_auth(hr))

    titles_returned = [
        row["job_title"] for row in response.json()["top_paid_job_titles"]
    ]
    assert titles_returned == [
        "Director",
        "Principal Engineer",
        "Staff Engineer",
        "Senior Engineer",
        "Engineer",
    ]


@pytest.mark.asyncio
async def test_top_paid_returns_fewer_than_5_when_fewer_titles_exist(
    client, db_session
):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(
        db_session, hr, email="a@example.com", job_title="Software Engineer",
        salary=80000,
    )
    _make_employee(
        db_session, hr, email="b@example.com", job_title="Product Manager",
        salary=120000,
    )

    response = await client.get("/api/insights/overview", headers=_auth(hr))

    titles = [row["job_title"] for row in response.json()["top_paid_job_titles"]]
    assert titles == ["Product Manager", "Software Engineer"]


@pytest.mark.asyncio
async def test_overview_unauthenticated_returns_401(client):
    response = await client.get("/api/insights/overview")
    assert response.status_code == 401
