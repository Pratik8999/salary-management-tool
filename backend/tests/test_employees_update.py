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
    first_name: str = "Ada",
    last_name: str = "Lovelace",
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
    db_session.refresh(employee)
    return employee


@pytest.mark.asyncio
async def test_hr_can_update_simple_fields(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await client.patch(
        f"/api/employees/{employee.id}",
        headers=_auth(hr),
        json={"job_title": "Senior Engineer", "salary": "75000.00"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["job_title"] == "Senior Engineer"
    assert body["salary"] == "75000.00"
    # untouched fields remain
    assert body["first_name"] == "Ada"
    assert body["country"] == "UK"
    assert body["department"] == "Engineering"


@pytest.mark.asyncio
async def test_partial_update_leaves_omitted_fields_alone(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await client.patch(
        f"/api/employees/{employee.id}",
        headers=_auth(hr),
        json={"country": "US"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["country"] == "US"
    assert body["first_name"] == "Ada"
    assert body["job_title"] == "Software Engineer"
    assert body["salary"] == "50000.00"


@pytest.mark.asyncio
async def test_update_department_to_existing_one(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    get_or_create_department(db_session, "Sales")
    employee = _make_employee(db_session, hr)

    response = await client.patch(
        f"/api/employees/{employee.id}",
        headers=_auth(hr),
        json={"department": "Sales"},
    )

    assert response.status_code == 200
    assert response.json()["department"] == "Sales"


@pytest.mark.asyncio
async def test_update_department_auto_creates_new_one(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await client.patch(
        f"/api/employees/{employee.id}",
        headers=_auth(hr),
        json={"department": "Research"},
    )

    assert response.status_code == 200
    assert response.json()["department"] == "Research"


@pytest.mark.asyncio
async def test_update_department_is_case_insensitive_match(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    get_or_create_department(db_session, "Engineering")
    employee = _make_employee(db_session, hr, department="Sales")

    response = await client.patch(
        f"/api/employees/{employee.id}",
        headers=_auth(hr),
        json={"department": "engineering"},
    )

    assert response.status_code == 200
    # Existing canonical name is preserved
    assert response.json()["department"] == "Engineering"


@pytest.mark.asyncio
async def test_can_deactivate_employee(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await client.patch(
        f"/api/employees/{employee.id}",
        headers=_auth(hr),
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_duplicate_email_returns_409(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="taken@example.com")
    employee = _make_employee(db_session, hr, email="ada@example.com")

    response = await client.patch(
        f"/api/employees/{employee.id}",
        headers=_auth(hr),
        json={"email": "taken@example.com"},
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_setting_email_to_current_value_is_ok(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr, email="ada@example.com")

    response = await client.patch(
        f"/api/employees/{employee.id}",
        headers=_auth(hr),
        json={"email": "ada@example.com", "job_title": "Architect"},
    )

    assert response.status_code == 200
    assert response.json()["job_title"] == "Architect"


@pytest.mark.asyncio
async def test_negative_salary_returns_422(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await client.patch(
        f"/api/employees/{employee.id}",
        headers=_auth(hr),
        json={"salary": "-1"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_future_date_joined_returns_422(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await client.patch(
        f"/api/employees/{employee.id}",
        headers=_auth(hr),
        json={"date_joined": "2099-01-01"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_returns_404_when_not_found(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.patch(
        "/api/employees/999999",
        headers=_auth(hr),
        json={"job_title": "Anything"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await client.patch(
        f"/api/employees/{employee.id}", json={"job_title": "X"}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_can_update_employee(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)

    response = await client.patch(
        f"/api/employees/{employee.id}",
        headers=_auth(admin),
        json={"job_title": "Architect"},
    )

    assert response.status_code == 200
    assert response.json()["job_title"] == "Architect"
