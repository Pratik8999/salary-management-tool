"""swap employees.department to FK

Revision ID: 333403a6aea2
Revises: bf4d71d16c88
Create Date: 2026-05-21 11:05:34.443966

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '333403a6aea2'
down_revision: Union[str, Sequence[str], None] = 'bf4d71d16c88'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        INSERT INTO departments (name, is_active, created_at, updated_at)
        SELECT MIN(department), true, now(), now()
        FROM employees
        GROUP BY lower(department)
        ON CONFLICT (lower(name)) DO NOTHING
        """
    )

    op.add_column(
        "employees", sa.Column("department_id", sa.Integer(), nullable=True)
    )
    op.execute(
        """
        UPDATE employees e
        SET department_id = d.id
        FROM departments d
        WHERE lower(d.name) = lower(e.department)
        """
    )
    op.alter_column("employees", "department_id", nullable=False)
    op.create_foreign_key(
        "fk_employees_department_id_departments",
        "employees",
        "departments",
        ["department_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_employees_department_id", "employees", ["department_id"]
    )

    op.drop_index("ix_employees_department", table_name="employees")
    op.drop_column("employees", "department")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "employees",
        sa.Column("department", sa.String(length=100), nullable=True),
    )
    op.execute(
        """
        UPDATE employees e
        SET department = d.name
        FROM departments d
        WHERE d.id = e.department_id
        """
    )
    op.alter_column("employees", "department", nullable=False)
    op.create_index("ix_employees_department", "employees", ["department"])

    op.drop_index("ix_employees_department_id", table_name="employees")
    op.drop_constraint(
        "fk_employees_department_id_departments",
        "employees",
        type_="foreignkey",
    )
    op.drop_column("employees", "department_id")
