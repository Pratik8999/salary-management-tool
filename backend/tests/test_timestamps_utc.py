from datetime import timedelta

from sqlalchemy import text

from app.models.user import User, UserRole


def test_db_session_timezone_is_utc(db_session):
    result = db_session.execute(text("SHOW timezone")).scalar_one()
    assert result == "UTC"


def test_user_timestamps_round_trip_as_utc(db_session):
    user = User(email="tz@example.com", role=UserRole.HR)
    user.set_password("x")
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)

    assert user.created_at.tzinfo is not None
    assert user.created_at.utcoffset() == timedelta(0)
    assert user.updated_at.tzinfo is not None
    assert user.updated_at.utcoffset() == timedelta(0)
