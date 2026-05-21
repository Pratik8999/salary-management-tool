"""CLI entry-point for the seed.

Usage (inside the backend dir):

    uv run python -m seed --count 10000

The script connects to the configured DATABASE_URL, ensures an admin user
exists (creating admin@example.com / admin123 if missing), then wipes
and re-seeds the employee data.
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


def _ensure_admin(db) -> User:
    admin = db.execute(
        select(User).where(User.email == DEFAULT_ADMIN_EMAIL)
    ).scalar_one_or_none()
    if admin is not None:
        return admin
    admin = User(email=DEFAULT_ADMIN_EMAIL, role=UserRole.ADMIN, is_active=True)
    admin.set_password(DEFAULT_ADMIN_PASSWORD)
    db.add(admin)
    db.flush()
    db.refresh(admin)
    return admin


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
        db.commit()
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
