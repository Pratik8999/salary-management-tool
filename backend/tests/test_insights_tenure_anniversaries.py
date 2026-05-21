from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.auth.jwt_handler import create_access_token
from app.departments.service import get_or_create_department
from app.models.employee import Employee, EmploymentType
from app.models.user import User, UserRole

# Hardcoded reference date so tests don't drift across year boundaries.
TODAY = date(2026, 5, 21)


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
    date_joined: date,
    department: str = "Engineering",
    is_active: bool = True,
) -> Employee:
    dept = get_or_create_department(db_session, department)
    emp = Employee(
        first_name="A",
        last_name="B",
        email=email,
        job_title="Software Engineer",
        country="UK",
        salary=Decimal("50000"),
        department_id=dept.id,
        employment_type=EmploymentType.FULL_TIME,
        date_joined=date_joined,
        is_active=is_active,
        created_by_id=hr.id,
    )
    db_session.add(emp)
    db_session.flush()
    return emp


@pytest.fixture(autouse=True)
def freeze_today(monkeypatch):
    """Pin app.insights.router.date.today() to a known value so the tests
    don't go stale as the real clock ticks past anniversaries."""
    import app.insights.router as router_mod

    class _Frozen(date):
        @classmethod
        def today(cls):  # type: ignore[override]
            return TODAY

    monkeypatch.setattr(router_mod, "date", _Frozen)


@pytest.mark.asyncio
async def test_anniversaries_returns_milestones_within_window(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    # Hits a 5-year milestone in 14 days (joined 2021-06-04).
    _make_employee(
        db_session, hr, email="five@example.com", date_joined=date(2021, 6, 4)
    )
    # Hits a 3-year milestone in 7 days (joined 2023-05-28).
    _make_employee(
        db_session, hr, email="three@example.com", date_joined=date(2023, 5, 28)
    )
    # Hits a 1-year milestone in 25 days (joined 2025-06-15).
    _make_employee(
        db_session, hr, email="one@example.com", date_joined=date(2025, 6, 15)
    )

    response = await client.get(
        "/api/insights/tenure/anniversaries", headers=_auth(hr)
    )

    assert response.status_code == 200
    body = response.json()
    by_email = {row["email"]: row for row in body}
    assert set(by_email) == {"five@example.com", "three@example.com", "one@example.com"}
    assert by_email["five@example.com"]["years"] == 5
    assert by_email["three@example.com"]["years"] == 3
    assert by_email["one@example.com"]["years"] == 1


@pytest.mark.asyncio
async def test_non_milestone_anniversaries_are_excluded(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    # 2-year anniversary in 5 days — not a milestone (we only flag 1/3/5/10).
    _make_employee(
        db_session, hr, email="two@example.com", date_joined=date(2024, 5, 26)
    )

    response = await client.get(
        "/api/insights/tenure/anniversaries", headers=_auth(hr)
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_anniversaries_outside_window_are_excluded(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    # 5-year anniversary is 90 days out — past the default 30-day window.
    _make_employee(
        db_session, hr, email="far@example.com", date_joined=date(2021, 8, 19)
    )

    response = await client.get(
        "/api/insights/tenure/anniversaries", headers=_auth(hr)
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_within_days_can_be_widened(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    # 5-year anniversary 90 days out, outside the default but inside 120.
    _make_employee(
        db_session, hr, email="far@example.com", date_joined=date(2021, 8, 19)
    )

    response = await client.get(
        "/api/insights/tenure/anniversaries?within_days=120", headers=_auth(hr)
    )

    assert response.status_code == 200
    assert [r["email"] for r in response.json()] == ["far@example.com"]


@pytest.mark.asyncio
async def test_inactive_employees_excluded(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(
        db_session,
        hr,
        email="gone@example.com",
        date_joined=date(2021, 6, 4),
        is_active=False,
    )

    response = await client.get(
        "/api/insights/tenure/anniversaries", headers=_auth(hr)
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_anniversaries_unauthenticated_returns_401(client):
    response = await client.get("/api/insights/tenure/anniversaries")
    assert response.status_code == 401
