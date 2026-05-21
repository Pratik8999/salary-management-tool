from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.department import Department


def get_or_create_department(db: Session, name: str) -> Department:
    cleaned = name.strip()
    existing = db.execute(
        select(Department).where(func.lower(Department.name) == cleaned.lower())
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    dept = Department(name=cleaned)
    db.add(dept)
    db.flush()
    return dept
