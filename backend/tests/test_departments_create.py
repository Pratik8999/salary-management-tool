import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.auth.jwt_handler import create_access_token
from app.main import app
from app.models.department import Department
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


@pytest_asyncio.fixture
async def client(db_session):
    from app.db.session import get_db

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_can_create_department(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)

    response = await client.post(
        "/api/departments",
        headers=_auth(admin),
        json={"name": "Engineering"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Engineering"
    assert body["is_active"] is True
    assert "id" in body

    dept = db_session.get(Department, body["id"])
    assert dept is not None
    assert dept.name == "Engineering"


@pytest.mark.asyncio
async def test_name_is_trimmed(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)

    response = await client.post(
        "/api/departments",
        headers=_auth(admin),
        json={"name": "  Finance  "},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Finance"


@pytest.mark.asyncio
async def test_rejects_case_insensitive_duplicate(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    db_session.add(Department(name="Engineering"))
    db_session.flush()

    response = await client.post(
        "/api/departments",
        headers=_auth(admin),
        json={"name": "engineering"},
    )

    assert response.status_code == 409
    assert "exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_blank_name_rejected(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)

    response = await client.post(
        "/api/departments",
        headers=_auth(admin),
        json={"name": "   "},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_hr_cannot_create_department(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.post(
        "/api/departments",
        headers=_auth(hr),
        json={"name": "Engineering"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_unauthenticated_returns_401(client):
    response = await client.post("/api/departments", json={"name": "Engineering"})
    assert response.status_code == 401
