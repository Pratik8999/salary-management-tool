import pytest

from app.auth.jwt_handler import create_access_token
from app.models.user import User, UserRole


def _seeded_user(db_session, *, email: str, role: UserRole, is_active: bool = True) -> User:
    user = User(email=email, role=role, is_active=is_active)
    user.set_password("any-password")
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)
    return user


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_admin_can_create_hr_user(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)

    response = await client.post(
        "/api/admin/users",
        headers=_auth(admin),
        json={"email": "new-hr@example.com", "password": "s3cret-pass", "role": "hr"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new-hr@example.com"
    assert body["role"] == "hr"
    assert body["is_active"] is True
    assert "id" in body
    assert "password" not in body
    assert "hashed_password" not in body


@pytest.mark.asyncio
async def test_created_user_password_is_hashed_in_db(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)

    response = await client.post(
        "/api/admin/users",
        headers=_auth(admin),
        json={"email": "new-hr@example.com", "password": "s3cret-pass", "role": "hr"},
    )
    assert response.status_code == 201

    created = db_session.query(User).filter_by(email="new-hr@example.com").one()
    assert created.hashed_password != "s3cret-pass"
    assert created.verify_password("s3cret-pass") is True


@pytest.mark.asyncio
async def test_duplicate_email_returns_409(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    _seeded_user(db_session, email="taken@example.com", role=UserRole.HR)

    response = await client.post(
        "/api/admin/users",
        headers=_auth(admin),
        json={"email": "taken@example.com", "password": "s3cret-pass", "role": "hr"},
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_hr_user_cannot_create_users(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.post(
        "/api/admin/users",
        headers=_auth(hr),
        json={"email": "new-hr@example.com", "password": "s3cret-pass", "role": "hr"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401(client):
    response = await client.post(
        "/api/admin/users",
        json={"email": "new-hr@example.com", "password": "s3cret-pass", "role": "hr"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_bad_body_returns_422(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)

    response = await client.post(
        "/api/admin/users",
        headers=_auth(admin),
        json={"email": "not-an-email", "password": "short", "role": "hr"},
    )

    assert response.status_code == 422
