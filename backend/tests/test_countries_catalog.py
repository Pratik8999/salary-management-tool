"""Tests for the canonical country reference catalog.

The catalog lives in `app.reference.countries` and is exposed at
`GET /api/countries`. The seed and `EmployeeRead.currency` both read
from the same source — that single-source-of-truth property is what
these tests pin down.
"""

import pytest

from app.auth.jwt_handler import create_access_token
from app.departments.service import get_or_create_department
from app.models.user import User, UserRole
from app.reference.countries import CATALOG, COUNTRY_NAMES, currency_for


def _seeded_user(db_session, *, email: str, role: UserRole) -> User:
    user = User(email=email, role=role, is_active=True)
    user.set_password("any-password")
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)
    return user


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_currency_for_known_country_is_iso_code():
    assert currency_for("India") == "INR"
    assert currency_for("Germany") == "EUR"
    assert currency_for("United States") == "USD"


def test_currency_for_is_case_insensitive():
    assert currency_for("india") == "INR"
    assert currency_for("UNITED KINGDOM") == "GBP"


def test_currency_for_unknown_country_is_none():
    assert currency_for("Atlantis") is None
    assert currency_for("UK") is None  # legacy free-text — intentional
    assert currency_for(None) is None
    assert currency_for("") is None


def test_seed_country_list_matches_catalog():
    # The seed used to keep its own COUNTRIES tuple — this assertion
    # protects against re-introducing that drift.
    from seed.generator import COUNTRIES as SEED_COUNTRIES

    assert SEED_COUNTRIES == COUNTRY_NAMES


@pytest.mark.asyncio
async def test_get_countries_returns_catalog(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.get("/api/countries", headers=_auth(hr))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == len(CATALOG)
    names = [row["name"] for row in body]
    assert names == list(COUNTRY_NAMES)
    india = next(row for row in body if row["name"] == "India")
    assert india["currency"] == "INR"


@pytest.mark.asyncio
async def test_get_countries_requires_auth(client):
    response = await client.get("/api/countries")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_employee_response_includes_currency(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    eng = get_or_create_department(db_session, "Engineering")

    payload = {
        "first_name": "Asha",
        "last_name": "Rao",
        "email": "asha.rao@example.com",
        "job_title": "Software Engineer",
        "country": "India",
        "salary": "1200000.00",
        "department_id": eng.id,
        "employment_type": "full_time",
        "date_joined": "2024-01-15",
    }
    response = await client.post(
        "/api/employees", headers=_auth(hr), json=payload
    )
    assert response.status_code == 201
    assert response.json()["currency"] == "INR"


@pytest.mark.asyncio
async def test_employee_with_unknown_country_has_null_currency(
    client, db_session
):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    eng = get_or_create_department(db_session, "Engineering")

    payload = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "job_title": "Software Engineer",
        "country": "UK",  # legacy free-text, intentionally not in catalog
        "salary": "50000.00",
        "department_id": eng.id,
        "employment_type": "full_time",
        "date_joined": "2024-01-15",
    }
    response = await client.post(
        "/api/employees", headers=_auth(hr), json=payload
    )
    assert response.status_code == 201
    assert response.json()["currency"] is None
