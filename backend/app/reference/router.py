from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.reference.countries import CATALOG

router = APIRouter(prefix="/api/countries", tags=["reference"])


class CountryOut(BaseModel):
    name: str
    currency: str


@router.get("", response_model=list[CountryOut])
def list_countries(
    _: User = Depends(get_current_user),
) -> list[CountryOut]:
    """Return the canonical country catalog with currency codes."""
    return [CountryOut(name=c.name, currency=c.currency) for c in CATALOG]
