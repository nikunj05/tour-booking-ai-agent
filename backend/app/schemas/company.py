from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class CompanyCreate(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    country_code: str = Field(..., max_length=10)
    phone: Optional[str] = Field(None, max_length=25)
    country: Optional[str] = Field(None, max_length=100)
    currency: str = Field(..., max_length=10)

class CompanyUpdate(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=150)
    country_code: str
    phone: Optional[str] = Field(None, max_length=15)
    country: Optional[str] = Field(None)
    status: str = Field(..., pattern="^(active|inactive)$")
    currency: str
