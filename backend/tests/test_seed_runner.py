"""Integration test for the seed runner against the transactional test DB.

We run with a tiny employee count to keep the suite fast — the bulk-insert
path is exercised the same way at 50 rows as it is at 10k.
"""

import pytest
from sqlalchemy import func, select

from app.models.department import Department
from app.models.employee import Employee
from app.models.user import User, UserRole
from seed.runner import run_seed


@pytest.fixture
def admin_user(db_session) -> User:
    user = User(email="admin@example.com", role=UserRole.ADMIN)
    user.set_password("admin123")
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)
    return user


def test_seed_creates_employees_and_departments(db_session, admin_user):
    run_seed(db_session, employee_count=50, creator_id=admin_user.id, seed=1)

    dept_count = db_session.execute(
        select(func.count()).select_from(Department)
    ).scalar_one()
    emp_count = db_session.execute(
        select(func.count()).select_from(Employee)
    ).scalar_one()

    assert dept_count >= 5
    assert emp_count == 50


def test_seed_is_idempotent(db_session, admin_user):
    run_seed(db_session, employee_count=20, creator_id=admin_user.id, seed=1)
    run_seed(db_session, employee_count=20, creator_id=admin_user.id, seed=2)

    emp_count = db_session.execute(
        select(func.count()).select_from(Employee)
    ).scalar_one()
    # Second run should have wiped the first batch, not piled on top.
    assert emp_count == 20


def test_seed_preserves_users(db_session, admin_user):
    run_seed(db_session, employee_count=10, creator_id=admin_user.id, seed=1)

    db_session.expire_all()
    user_count = db_session.execute(
        select(func.count()).select_from(User)
    ).scalar_one()
    assert user_count >= 1
    assert db_session.get(User, admin_user.id) is not None
