import pytest

from app.auth.jwt_handler import create_access_token
from app.models.user import User, UserRole


def _make_user(
    db_session,
    *,
    email: str,
    role: UserRole = UserRole.HR,
    is_active: bool = True,
) -> User:
    user = User(email=email, role=role, is_active=is_active)
    user.set_password("any-password")
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)
    return user


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_me_without_token_returns_401(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_invalid_token_returns_401(client):
    response = await client.get("/api/auth/me", headers=_auth("garbage"))
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_current_admin_user(client, db_session):
    user = _make_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    token = create_access_token(subject=str(user.id), role=user.role.value)

    response = await client.get("/api/auth/me", headers=_auth(token))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == user.id
    assert body["email"] == "admin@example.com"
    assert body["role"] == "admin"
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_me_returns_current_hr_user(client, db_session):
    user = _make_user(db_session, email="hr@example.com", role=UserRole.HR)
    token = create_access_token(subject=str(user.id), role=user.role.value)

    response = await client.get("/api/auth/me", headers=_auth(token))

    assert response.status_code == 200
    assert response.json()["role"] == "hr"
