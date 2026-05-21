"""Unit tests for the seed row generator.

These exercise the pure-Python row builder in isolation — no DB, no I/O.
The DB-touching seed runner is covered separately in test_seed_runner.py.
"""

from datetime import date

import pytest

from seed.generator import (
    DEPARTMENT_NAMES,
    EMPLOYMENT_TYPES,
    JOB_TITLES,
    SALARY_BAND_BY_TITLE,
    build_employee_rows,
)


def test_produces_the_requested_number_of_rows():
    rows = build_employee_rows(
        count=50,
        department_ids=[1, 2, 3],
        creator_id=1,
        seed=42,
    )
    assert len(rows) == 50


def test_each_row_has_all_required_fields():
    rows = build_employee_rows(
        count=10, department_ids=[1], creator_id=1, seed=1
    )
    required = {
        "first_name",
        "last_name",
        "email",
        "job_title",
        "country",
        "salary",
        "department_id",
        "employment_type",
        "date_joined",
        "created_by_id",
        "is_active",
    }
    for row in rows:
        assert required.issubset(row.keys())


def test_emails_are_unique_in_the_batch():
    rows = build_employee_rows(
        count=500, department_ids=[1, 2], creator_id=1, seed=7
    )
    emails = [r["email"] for r in rows]
    assert len(emails) == len(set(emails))


def test_department_ids_only_come_from_provided_set():
    rows = build_employee_rows(
        count=200, department_ids=[10, 20, 30], creator_id=1, seed=3
    )
    assert {r["department_id"] for r in rows} <= {10, 20, 30}


def test_employment_type_values_are_valid():
    rows = build_employee_rows(
        count=200, department_ids=[1], creator_id=1, seed=11
    )
    assert {r["employment_type"] for r in rows} <= set(EMPLOYMENT_TYPES)


def test_job_titles_come_from_the_catalog():
    rows = build_employee_rows(
        count=200, department_ids=[1], creator_id=1, seed=11
    )
    assert {r["job_title"] for r in rows} <= set(JOB_TITLES)


def test_salary_stays_in_the_band_for_the_job_title():
    rows = build_employee_rows(
        count=500, department_ids=[1], creator_id=1, seed=21
    )
    for r in rows:
        lo, hi = SALARY_BAND_BY_TITLE[r["job_title"]]
        assert lo <= float(r["salary"]) <= hi


def test_date_joined_is_not_in_the_future():
    rows = build_employee_rows(
        count=200, department_ids=[1], creator_id=1, seed=5
    )
    today = date.today()
    for r in rows:
        assert r["date_joined"] <= today


def test_creator_id_is_propagated():
    rows = build_employee_rows(
        count=20, department_ids=[1], creator_id=99, seed=0
    )
    assert all(r["created_by_id"] == 99 for r in rows)


def test_deterministic_with_a_fixed_seed():
    a = build_employee_rows(count=30, department_ids=[1, 2], creator_id=1, seed=123)
    b = build_employee_rows(count=30, department_ids=[1, 2], creator_id=1, seed=123)
    assert a == b


def test_department_catalog_is_non_empty():
    assert len(DEPARTMENT_NAMES) >= 5
