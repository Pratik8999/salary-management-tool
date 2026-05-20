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
async def test_admin_can_change_user_role(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    target = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.patch(
        f"/api/admin/users/{target.id}", headers=_auth(admin), json={"role": "admin"}
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_admin_can_deactivate_user(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    target = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.patch(
        f"/api/admin/users/{target.id}", headers=_auth(admin), json={"is_active": False}
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_admin_can_reset_password(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    target = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.patch(
        f"/api/admin/users/{target.id}",
        headers=_auth(admin),
        json={"password": "brand-new-pass"},
    )

    assert response.status_code == 200
    assert "password" not in response.json()
    assert "hashed_password" not in response.json()

    db_session.refresh(target)
    assert target.verify_password("brand-new-pass") is True


@pytest.mark.asyncio
async def test_admin_cannot_deactivate_themselves(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)

    response = await client.patch(
        f"/api/admin/users/{admin.id}", headers=_auth(admin), json={"is_active": False}
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_admin_cannot_demote_themselves(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)

    response = await client.patch(
        f"/api/admin/users/{admin.id}", headers=_auth(admin), json={"role": "hr"}
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_unknown_id_returns_404(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)

    response = await client.patch(
        "/api/admin/users/99999", headers=_auth(admin), json={"is_active": False}
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_hr_cannot_update_users(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    target = _seeded_user(db_session, email="other@example.com", role=UserRole.HR)

    response = await client.patch(
        f"/api/admin/users/{target.id}", headers=_auth(hr), json={"is_active": False}
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_update_returns_401(client, db_session):
    target = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.patch(
        f"/api/admin/users/{target.id}", json={"is_active": False}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_password_too_short_returns_422(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    target = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.patch(
        f"/api/admin/users/{target.id}", headers=_auth(admin), json={"password": "short"}
    )

    assert response.status_code == 422
