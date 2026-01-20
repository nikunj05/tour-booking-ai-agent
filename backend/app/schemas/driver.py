from pydantic import BaseModel
from typing import Optional

class DriverBase(BaseModel):
    name: str
    vehicle_type: str
    vehicle_number: str
    seats: int
    phone: str
    image: Optional[str] = None

class DriverCreate(DriverBase):
    pass

class DriverUpdate(DriverBase):
    pass