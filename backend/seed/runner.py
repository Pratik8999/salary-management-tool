"""Bulk-seed runner.

Idempotent by truncate-and-insert: every run wipes employees + their
documents and the department catalog, then re-creates a fresh set. Users
are left alone so the admin login survives across seeds.

The actual row generation lives in `seed.generator`. This module is the
DB-touching shell around it.
"""

from __future__ import annotations

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.employee import Employee
from app.models.employee_document import EmployeeDocument
from seed.generator import DEPARTMENT_NAMES, build_employee_rows


def _wipe(db: Session) -> None:
    # Documents first; the employees FK has ON DELETE CASCADE for files,
    # but the explicit delete keeps the row count predictable for tests
    # that don't seed documents.
    db.execute(delete(EmployeeDocument))
    db.execute(delete(Employee))
    db.execute(delete(Department))
    db.flush()


def _seed_departments(db: Session) -> list[int]:
    db.execute(
        insert(Department).values([{"name": name} for name in DEPARTMENT_NAMES])
    )
    db.flush()
    ids = db.execute(
        select(Department.id).order_by(Department.id)
    ).scalars().all()
    return list(ids)


def run_seed(
    db: Session,
    *,
    employee_count: int,
    creator_id: int,
    seed: int = 0,
    chunk_size: int = 1000,
) -> None:
    """Wipe employee data and re-seed.

    `creator_id` must point at an existing user — the FK on
    employees.created_by_id is ON DELETE RESTRICT, so passing a stale id
    will surface as an IntegrityError at flush time.
    """
    _wipe(db)
    department_ids = _seed_departments(db)

    rows = build_employee_rows(
        count=employee_count,
        department_ids=department_ids,
        creator_id=creator_id,
        seed=seed,
    )

    # Insert in chunks so 10k rows don't pile up in a single statement;
    # SQLAlchemy/psycopg are fine with one big values() list but the
    # chunk loop keeps memory + log lines reasonable.
    for start in range(0, len(rows), chunk_size):
        batch = rows[start : start + chunk_size]
        db.execute(insert(Employee).values(batch))

    db.flush()
