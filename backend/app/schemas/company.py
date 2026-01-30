from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class CompanyCreate(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    country_code: str
    phone: Optional[str] = Field(
        min_length=7,
        max_length=15,
        description="Optional phone number"
    )
    country: Optional[str] = Field(None)
    currency: str

class CompanyUpdate(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=150)
    country_code: str
    phone: Optional[str] = Field(
        min_length=7,
        max_length=15,
    )
    country: Optional[str] = Field(None)
    status: str = Field(..., pattern="^(active|inactive)$")
    currency: str
