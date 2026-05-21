"""Pure-python row builder for the employee seed.

Kept I/O- and DB-free so it can be unit-tested in isolation. The runner
in `seed.run` is responsible for reading the name files, opening a DB
session, and feeding the rows produced here into a bulk insert.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

# Catalog of departments the seed assumes will exist in the database.
# The runner is responsible for ensuring rows exist for each name and
# wiring up the resulting ids before calling build_employee_rows.
DEPARTMENT_NAMES: tuple[str, ...] = (
    "Engineering",
    "Sales",
    "Marketing",
    "Human Resources",
    "Finance",
    "Operations",
    "Customer Success",
    "Design",
    "Legal",
    "Information Technology",
)

# Each band is (min_salary, max_salary) in whole units of the local currency.
# The numbers are intentionally rough — the assessment only cares that the
# distribution is plausible, not that it matches a particular market.
SALARY_BAND_BY_TITLE: dict[str, tuple[int, int]] = {
    "Software Engineer": (60_000, 140_000),
    "Senior Software Engineer": (110_000, 200_000),
    "Engineering Manager": (140_000, 240_000),
    "Product Manager": (100_000, 200_000),
    "Designer": (60_000, 130_000),
    "Data Analyst": (55_000, 120_000),
    "Data Scientist": (90_000, 180_000),
    "DevOps Engineer": (90_000, 170_000),
    "QA Engineer": (50_000, 110_000),
    "Sales Executive": (45_000, 110_000),
    "Sales Manager": (90_000, 180_000),
    "Marketing Specialist": (50_000, 100_000),
    "Marketing Manager": (90_000, 160_000),
    "HR Business Partner": (70_000, 130_000),
    "Recruiter": (50_000, 95_000),
    "Accountant": (55_000, 110_000),
    "Finance Analyst": (65_000, 130_000),
    "Operations Manager": (80_000, 150_000),
    "Customer Success Manager": (65_000, 130_000),
    "Support Engineer": (45_000, 95_000),
    "Legal Counsel": (110_000, 220_000),
    "IT Administrator": (50_000, 110_000),
}

JOB_TITLES: tuple[str, ...] = tuple(SALARY_BAND_BY_TITLE.keys())

EMPLOYMENT_TYPES: tuple[str, ...] = (
    "full_time",
    "part_time",
    "contract",
    "intern",
)

# Weighted so the bulk of seeded employees look like permanent staff,
# with realistic minorities of contractors and interns. The order matches
# EMPLOYMENT_TYPES.
EMPLOYMENT_TYPE_WEIGHTS: tuple[int, ...] = (78, 8, 10, 4)

COUNTRIES: tuple[str, ...] = (
    "India",
    "United States",
    "United Kingdom",
    "Canada",
    "Germany",
    "Australia",
    "Singapore",
    "Netherlands",
    "Ireland",
    "United Arab Emirates",
)


def load_name_list(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def build_employee_rows(
    *,
    count: int,
    department_ids: list[int],
    creator_id: int,
    seed: int,
    first_names: list[str] | None = None,
    last_names: list[str] | None = None,
    today: date | None = None,
) -> list[dict]:
    """Produce `count` employee row-dicts ready for a bulk insert.

    Each row is a plain dict so the caller can hand it straight to
    `session.execute(insert(Employee).values([...]))` without paying for
    ORM object construction on 10k rows.
    """
    if count < 0:
        raise ValueError("count must be non-negative")
    if not department_ids:
        raise ValueError("at least one department_id is required")

    here = Path(__file__).parent
    first = first_names or load_name_list(here / "first_names.txt")
    last = last_names or load_name_list(here / "last_names.txt")
    if not first or not last:
        raise ValueError("name lists must be non-empty")

    today = today or date.today()
    rng = random.Random(seed)

    rows: list[dict] = []
    for i in range(count):
        f = rng.choice(first)
        l = rng.choice(last)
        # Append the row index so we don't have to fight for global
        # uniqueness when the name pool is smaller than `count`.
        email = f"{f.lower()}.{l.lower()}.{i + 1}@example.com"

        title = rng.choice(JOB_TITLES)
        lo, hi = SALARY_BAND_BY_TITLE[title]
        # Round to the nearest 1,000 so the numbers look like real
        # payroll, not three decimal digits of noise.
        salary = Decimal(rng.randrange(lo, hi + 1, 1_000))

        employment_type = rng.choices(
            EMPLOYMENT_TYPES, weights=EMPLOYMENT_TYPE_WEIGHTS, k=1
        )[0]

        # Hire dates from somewhere in the last 10 years.
        days_back = rng.randint(0, 365 * 10)
        joined = today - timedelta(days=days_back)

        rows.append(
            {
                "first_name": f,
                "last_name": l,
                "email": email,
                "job_title": title,
                "country": rng.choice(COUNTRIES),
                "salary": salary,
                "department_id": rng.choice(department_ids),
                "employment_type": employment_type,
                "date_joined": joined,
                "created_by_id": creator_id,
                "is_active": True,
            }
        )
    return rows
