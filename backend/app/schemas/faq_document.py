from pydantic import BaseModel
from datetime import datetime


class FAQDocumentCreate(BaseModel):
    company_id: int
    title: str
    content: str


class FAQDocumentResponse(BaseModel):
    id: int
    company_id: int
    title: str
    content: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
