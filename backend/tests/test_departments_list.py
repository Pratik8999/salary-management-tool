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


def _seed_dept(db_session, *, name: str, is_active: bool = True) -> Department:
    dept = Department(name=name, is_active=is_active)
    db_session.add(dept)
    db_session.flush()
    db_session.refresh(dept)
    return dept


@pytest.mark.asyncio
async def test_hr_can_list_active_departments(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _seed_dept(db_session, name="Engineering")
    _seed_dept(db_session, name="Finance")
    _seed_dept(db_session, name="Legacy", is_active=False)

    response = await client.get("/api/departments", headers=_auth(hr))

    assert response.status_code == 200
    body = response.json()
    names = [d["name"] for d in body]
    assert names == ["Engineering", "Finance"]
    for dept in body:
        assert "id" in dept
        assert "is_active" in dept
        assert dept["is_active"] is True


@pytest.mark.asyncio
async def test_admin_can_list_all_with_include_inactive(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    _seed_dept(db_session, name="Engineering")
    _seed_dept(db_session, name="Legacy", is_active=False)

    response = await client.get(
        "/api/departments?include_inactive=true", headers=_auth(admin)
    )

    assert response.status_code == 200
    body = response.json()
    names = sorted(d["name"] for d in body)
    assert names == ["Engineering", "Legacy"]


@pytest.mark.asyncio
async def test_hr_cannot_include_inactive_departments(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _seed_dept(db_session, name="Engineering")
    _seed_dept(db_session, name="Legacy", is_active=False)

    response = await client.get(
        "/api/departments?include_inactive=true", headers=_auth(hr)
    )

    assert response.status_code == 200
    names = [d["name"] for d in response.json()]
    assert names == ["Engineering"]


@pytest.mark.asyncio
async def test_list_unauthenticated_returns_401(client):
    response = await client.get("/api/departments")
    assert response.status_code == 401
