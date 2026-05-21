"""CLI entry-point for the seed.

Usage (inside the backend dir):

    uv run python -m seed --count 10000

The script connects to the configured DATABASE_URL, ensures a default
admin + HR user exist (admin@example.com / admin123 and hr@example.com /
hr123 if missing), then wipes and re-seeds the employee data.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models.user import User, UserRole
from seed.runner import run_seed

DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_HR_EMAIL = "hr@example.com"
DEFAULT_HR_PASSWORD = "hr123"


def _ensure_user(db, *, email: str, password: str, role: UserRole) -> User:
    existing = db.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    user = User(email=email, role=role, is_active=True)
    user.set_password(password)
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


def _ensure_admin(db) -> User:
    return _ensure_user(
        db,
        email=DEFAULT_ADMIN_EMAIL,
        password=DEFAULT_ADMIN_PASSWORD,
        role=UserRole.ADMIN,
    )


def _ensure_hr(db) -> User:
    return _ensure_user(
        db,
        email=DEFAULT_HR_EMAIL,
        password=DEFAULT_HR_PASSWORD,
        role=UserRole.HR,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed the employee table.")
    parser.add_argument(
        "--count", type=int, default=10_000, help="number of employees to seed"
    )
    parser.add_argument(
        "--seed", type=int, default=0, help="random seed for reproducibility"
    )
    args = parser.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2

    engine = create_engine(database_url, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)
    with SessionLocal() as db:
        admin = _ensure_admin(db)
        hr = _ensure_hr(db)
        db.commit()
        print(f"Default users ready: {admin.email} (admin), {hr.email} (hr)")
        print(f"Seeding {args.count} employees (creator={admin.email})...")
        started = time.monotonic()
        run_seed(
            db, employee_count=args.count, creator_id=admin.id, seed=args.seed
        )
        db.commit()
        elapsed = time.monotonic() - started
    rate = args.count / elapsed if elapsed > 0 else float("inf")
    print(f"Done in {elapsed:.2f}s ({rate:,.0f} rows/sec).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
