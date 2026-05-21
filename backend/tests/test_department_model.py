import pytest
from sqlalchemy.exc import IntegrityError

from app.models.department import Department


def test_persists_with_required_fields(db_session):
    dept = Department(name="Engineering")
    db_session.add(dept)
    db_session.flush()
    db_session.refresh(dept)

    assert dept.id is not None
    assert dept.name == "Engineering"
    assert dept.is_active is True
    assert dept.created_at is not None
    assert dept.updated_at is not None


def test_name_is_required(db_session):
    db_session.add(Department())
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_name_is_unique(db_session):
    db_session.add(Department(name="Engineering"))
    db_session.flush()

    db_session.add(Department(name="Engineering"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_name_uniqueness_is_case_insensitive(db_session):
    db_session.add(Department(name="Engineering"))
    db_session.flush()

    db_session.add(Department(name="engineering"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_is_active_defaults_to_true(db_session):
    dept = Department(name="Sales")
    db_session.add(dept)
    db_session.flush()
    db_session.refresh(dept)
    assert dept.is_active is True


def test_can_be_deactivated(db_session):
    dept = Department(name="Legacy", is_active=False)
    db_session.add(dept)
    db_session.flush()
    db_session.refresh(dept)
    assert dept.is_active is False
