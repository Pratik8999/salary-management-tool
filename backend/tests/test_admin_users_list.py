import pytest

from app.auth.jwt_handler import create_access_token
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


@pytest.mark.asyncio
async def test_admin_lists_all_users_ordered_by_id(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    hr1 = _seeded_user(db_session, email="hr1@example.com", role=UserRole.HR)
    hr2 = _seeded_user(db_session, email="hr2@example.com", role=UserRole.HR)

    response = await client.get("/api/admin/users", headers=_auth(admin))

    assert response.status_code == 200
    body = response.json()
    ids = [u["id"] for u in body]
    assert ids == sorted(ids)
    emails = [u["email"] for u in body]
    assert {"admin@example.com", "hr1@example.com", "hr2@example.com"} <= set(emails)
    assert all("hashed_password" not in u and "password" not in u for u in body)
    # spot-check shape
    sample = next(u for u in body if u["email"] == hr1.email)
    assert sample["role"] == "hr"
    assert sample["is_active"] is True


@pytest.mark.asyncio
async def test_pagination_respects_limit_and_offset(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    for i in range(5):
        _seeded_user(db_session, email=f"hr{i}@example.com", role=UserRole.HR)

    page1 = await client.get("/api/admin/users?limit=2&offset=0", headers=_auth(admin))
    page2 = await client.get("/api/admin/users?limit=2&offset=2", headers=_auth(admin))

    assert page1.status_code == 200
    assert page2.status_code == 200
    ids1 = [u["id"] for u in page1.json()]
    ids2 = [u["id"] for u in page2.json()]
    assert len(ids1) == 2 and len(ids2) == 2
    assert set(ids1).isdisjoint(ids2)


@pytest.mark.asyncio
async def test_limit_out_of_bounds_returns_422(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)

    response = await client.get("/api/admin/users?limit=500", headers=_auth(admin))
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_hr_cannot_list_users(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.get("/api/admin/users", headers=_auth(hr))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_list_returns_401(client):
    response = await client.get("/api/admin/users")
    assert response.status_code == 401
