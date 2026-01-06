from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class AgentCreate(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    phone: Optional[str] = Field(
        min_length=10,
        max_length=15,
        description="Optional phone number"
    )
    currency: str

class AgentUpdate(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=150)
    phone: Optional[str] = Field(
        min_length=10,
        max_length=15,
    )
    status: str = Field(..., pattern="^(active|inactive)$")
    currency: str
