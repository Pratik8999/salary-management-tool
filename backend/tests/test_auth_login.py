import pytest

from app.models.user import User, UserRole


def _make_user(db_session, *, email: str, password: str, role=UserRole.HR, is_active: bool = True) -> User:
    user = User(email=email, role=role, is_active=is_active)
    user.set_password(password)
    db_session.add(user)
    db_session.flush()
    return user


@pytest.mark.asyncio
async def test_login_with_valid_credentials_returns_access_token(client, db_session):
    _make_user(db_session, email="hr@example.com", password="correct-horse")

    response = await client.post(
        "/api/auth/login",
        data={"username": "hr@example.com", "password": "correct-horse"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and body["access_token"]


@pytest.mark.asyncio
async def test_login_with_unknown_email_says_email_does_not_exist(client):
    response = await client.post(
        "/api/auth/login",
        data={"username": "ghost@example.com", "password": "anything"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Email does not exist"


@pytest.mark.asyncio
async def test_login_inactive_user_says_email_does_not_exist(client, db_session):
    _make_user(
        db_session, email="inactive@example.com", password="correct-horse", is_active=False
    )

    response = await client.post(
        "/api/auth/login",
        data={"username": "inactive@example.com", "password": "correct-horse"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Email does not exist"


@pytest.mark.asyncio
async def test_login_with_wrong_password_says_password_incorrect(client, db_session):
    _make_user(db_session, email="hr@example.com", password="correct-horse")

    response = await client.post(
        "/api/auth/login",
        data={"username": "hr@example.com", "password": "wrong-one"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Password is incorrect"
