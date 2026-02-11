from pydantic import BaseModel
from typing import Optional

class DriverBase(BaseModel):
    name: str
    country_code: str
    phone: str
    is_active: bool
    image: Optional[str] = None

class DriverCreate(DriverBase):
    pass

class DriverUpdate(DriverBase):
    pass