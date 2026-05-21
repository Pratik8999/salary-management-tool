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
    email: str = "ada@example.com",
    is_active: bool = True,
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
        is_active=is_active,
        created_by_id=hr.id,
    )
    db_session.add(employee)
    db_session.flush()
    db_session.refresh(employee)
    return employee


@pytest.mark.asyncio
async def test_hr_can_soft_delete_employee(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await client.delete(
        f"/api/employees/{employee.id}", headers=_auth(hr)
    )

    assert response.status_code == 204

    db_session.expire(employee)
    refreshed = db_session.get(Employee, employee.id)
    assert refreshed is not None
    assert refreshed.is_active is False


@pytest.mark.asyncio
async def test_delete_is_idempotent_for_already_inactive(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr, is_active=False)

    response = await client.delete(
        f"/api/employees/{employee.id}", headers=_auth(hr)
    )

    assert response.status_code == 204
    db_session.expire(employee)
    assert db_session.get(Employee, employee.id).is_active is False


@pytest.mark.asyncio
async def test_deleted_employee_hidden_from_default_list(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    await client.delete(f"/api/employees/{employee.id}", headers=_auth(hr))

    response = await client.get("/api/employees", headers=_auth(hr))
    assert response.status_code == 200
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_deleted_employee_shows_with_include_inactive(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    await client.delete(f"/api/employees/{employee.id}", headers=_auth(hr))

    response = await client.get(
        "/api/employees?include_inactive=true", headers=_auth(hr)
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_deleted_employee_still_fetchable_by_id(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    await client.delete(f"/api/employees/{employee.id}", headers=_auth(hr))

    response = await client.get(
        f"/api/employees/{employee.id}", headers=_auth(hr)
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_returns_404_when_not_found(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.delete(
        "/api/employees/999999", headers=_auth(hr)
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await client.delete(f"/api/employees/{employee.id}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_cannot_delete_employee(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)

    response = await client.delete(
        f"/api/employees/{employee.id}", headers=_auth(admin)
    )
    assert response.status_code == 403
