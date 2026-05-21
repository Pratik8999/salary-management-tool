from decimal import Decimal

from pydantic import BaseModel


class SalaryByCountry(BaseModel):
    country: str
    count: int
    min: Decimal
    max: Decimal
    avg: Decimal
