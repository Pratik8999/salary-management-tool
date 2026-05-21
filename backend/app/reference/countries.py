"""Canonical country catalog with ISO 4217 currency codes.

This is reference data, not user data — it doesn't change per-tenant or
per-request — so it lives in code rather than the database. The seed
script and the public `/api/countries` endpoint both read from here,
and the employee/insights responses derive `currency` from this map
instead of letting the frontend guess.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CountryEntry:
    name: str
    currency: str  # ISO 4217 code


# Order matches what the seed used historically, so a fresh seed produces
# the same employee mix as before. Add new entries at the bottom.
CATALOG: tuple[CountryEntry, ...] = (
    CountryEntry("India", "INR"),
    CountryEntry("United States", "USD"),
    CountryEntry("United Kingdom", "GBP"),
    CountryEntry("Canada", "CAD"),
    CountryEntry("Germany", "EUR"),
    CountryEntry("Australia", "AUD"),
    CountryEntry("Singapore", "SGD"),
    CountryEntry("Netherlands", "EUR"),
    CountryEntry("Ireland", "EUR"),
    CountryEntry("United Arab Emirates", "AED"),
)

COUNTRY_NAMES: tuple[str, ...] = tuple(entry.name for entry in CATALOG)

_CURRENCY_BY_NAME: dict[str, str] = {
    entry.name.lower(): entry.currency for entry in CATALOG
}


def currency_for(country: str | None) -> str | None:
    """Return the ISO 4217 currency code for `country`, or None if unknown.

    Lookup is case-insensitive on the canonical name. Historical free-text
    countries (e.g. "UK") are intentionally not mapped — the front-end
    should treat a null currency as "render the bare amount".
    """
    if not country:
        return None
    return _CURRENCY_BY_NAME.get(country.lower())
