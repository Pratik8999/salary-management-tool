import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_admin, get_current_hr, get_current_user
from app.auth.jwt_handler import create_access_token
from app.db.session import get_db
from app.models.user import User, UserRole


def _seeded_user(db_session, *, email: str, role: UserRole, is_active: bool = True) -> User:
    user = User(email=email, role=role, is_active=is_active)
    user.set_password("any-password")
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)
    return user


def _token_for(user: User) -> str:
    return create_access_token(subject=str(user.id), role=user.role.value)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def protected_client(db_session):
    """Tiny FastAPI app exposing each dependency through a route, so we can
    test the deps end-to-end without mounting them on the real app yet."""
    test_app = FastAPI()

    @test_app.get("/me")
    def me(user: User = Depends(get_current_user)):
        return {"id": user.id, "email": user.email, "role": user.role.value}

    @test_app.get("/admin-only")
    def admin_only(user: User = Depends(get_current_admin)):
        return {"id": user.id}

    @test_app.get("/hr-only")
    def hr_only(user: User = Depends(get_current_hr)):
        return {"id": user.id}

    def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# --- get_current_user ---


@pytest.mark.asyncio
async def test_missing_token_returns_401(protected_client):
    response = await protected_client.get("/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_returns_401(protected_client):
    response = await protected_client.get("/me", headers=_auth("not-a-real-token"))
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_valid_token_for_deleted_user_returns_401(protected_client, db_session):
    user = _seeded_user(db_session, email="ghost@example.com", role=UserRole.HR)
    token = _token_for(user)
    db_session.delete(user)
    db_session.flush()

    response = await protected_client.get("/me", headers=_auth(token))
    assert response.status_code == 401
    assert response.json()["detail"] == "Email does not exist"


@pytest.mark.asyncio
async def test_valid_token_for_inactive_user_returns_401(protected_client, db_session):
    user = _seeded_user(db_session, email="inactive@example.com", role=UserRole.HR)
    token = _token_for(user)
    user.is_active = False
    db_session.flush()

    response = await protected_client.get("/me", headers=_auth(token))
    assert response.status_code == 401
    assert response.json()["detail"] == "Email does not exist"


@pytest.mark.asyncio
async def test_valid_token_for_active_user_returns_user(protected_client, db_session):
    user = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    token = _token_for(user)

    response = await protected_client.get("/me", headers=_auth(token))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "hr@example.com"
    assert body["role"] == "hr"
    assert body["id"] == user.id


# --- get_current_admin ---


@pytest.mark.asyncio
async def test_admin_endpoint_accepts_admin(protected_client, db_session):
    user = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    token = _token_for(user)

    response = await protected_client.get("/admin-only", headers=_auth(token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_admin_endpoint_rejects_hr(protected_client, db_session):
    user = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    token = _token_for(user)

    response = await protected_client.get("/admin-only", headers=_auth(token))
    assert response.status_code == 403


# --- get_current_hr ---


@pytest.mark.asyncio
async def test_hr_endpoint_accepts_hr(protected_client, db_session):
    user = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    token = _token_for(user)

    response = await protected_client.get("/hr-only", headers=_auth(token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_hr_endpoint_rejects_admin(protected_client, db_session):
    user = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    token = _token_for(user)

    response = await protected_client.get("/hr-only", headers=_auth(token))
    assert response.status_code == 403
