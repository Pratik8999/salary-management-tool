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


def _seed_dept(db_session, *, name: str, is_active: bool = True) -> Department:
    dept = Department(name=name, is_active=is_active)
    db_session.add(dept)
    db_session.flush()
    db_session.refresh(dept)
    return dept


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
async def test_admin_can_rename_department(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    dept = _seed_dept(db_session, name="Eng")

    response = await client.patch(
        f"/api/departments/{dept.id}",
        headers=_auth(admin),
        json={"name": "Engineering"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Engineering"
    db_session.expire_all()
    assert db_session.get(Department, dept.id).name == "Engineering"


@pytest.mark.asyncio
async def test_admin_can_deactivate_department(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    dept = _seed_dept(db_session, name="Legacy")

    response = await client.patch(
        f"/api/departments/{dept.id}",
        headers=_auth(admin),
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_rename_to_existing_case_insensitive_name_rejected(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    _seed_dept(db_session, name="Engineering")
    other = _seed_dept(db_session, name="Sales")

    response = await client.patch(
        f"/api/departments/{other.id}",
        headers=_auth(admin),
        json={"name": "engineering"},
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_renaming_to_own_name_with_different_case_is_fine(client, db_session):
    """Renaming Engineering -> ENGINEERING should not 409 against itself."""
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    dept = _seed_dept(db_session, name="Engineering")

    response = await client.patch(
        f"/api/departments/{dept.id}",
        headers=_auth(admin),
        json={"name": "ENGINEERING"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "ENGINEERING"


@pytest.mark.asyncio
async def test_404_when_department_missing(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)

    response = await client.patch(
        "/api/departments/999999",
        headers=_auth(admin),
        json={"name": "Anything"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_hr_cannot_update_department(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    dept = _seed_dept(db_session, name="Eng")

    response = await client.patch(
        f"/api/departments/{dept.id}",
        headers=_auth(hr),
        json={"name": "Engineering"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_unauthenticated_returns_401(client, db_session):
    dept = _seed_dept(db_session, name="Eng")
    response = await client.patch(
        f"/api/departments/{dept.id}", json={"name": "Engineering"}
    )
    assert response.status_code == 401
