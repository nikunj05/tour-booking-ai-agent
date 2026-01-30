from pydantic import BaseModel, Field
from typing import Optional

class TourPackageCreate(BaseModel):
    title: str = Field(..., min_length=3)
    description: str
    country: str
    city: str
    currency: str
    price: float = Field(..., gt=0)
    itinerary: Optional[str] = None
    excludes: Optional[str] = None

class TourPackageUpdate(BaseModel):
    title: str
    description: str
    country: str
    city: str
    currency: str
    price: float
    itinerary: Optional[str]
    excludes: Optional[str]
    status: str = Field(pattern="^(active|inactive)$")
