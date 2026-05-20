import pytest

from app.models.user import User, UserRole


def test_set_password_stores_hash_not_plaintext():
    user = User(email="admin@example.com", role=UserRole.ADMIN)
    user.set_password("s3cret-pa$$")

    assert user.hashed_password is not None
    assert user.hashed_password != "s3cret-pa$$"
    assert "s3cret-pa$$" not in user.hashed_password


def test_verify_password_round_trips():
    user = User(email="hr@example.com", role=UserRole.HR)
    user.set_password("correct-horse")

    assert user.verify_password("correct-horse") is True


def test_verify_password_rejects_wrong_password():
    user = User(email="hr@example.com", role=UserRole.HR)
    user.set_password("correct-horse")

    assert user.verify_password("battery-staple") is False


def test_role_enum_accepts_admin_and_hr():
    assert UserRole("admin") is UserRole.ADMIN
    assert UserRole("hr") is UserRole.HR


def test_role_enum_rejects_unknown_value():
    with pytest.raises(ValueError):
        UserRole("guest")
