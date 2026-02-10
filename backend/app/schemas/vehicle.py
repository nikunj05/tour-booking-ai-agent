from pydantic import BaseModel
from typing import Optional

class VehicleBase(BaseModel):
    name: str
    vehicle_type: str
    vehicle_number: str
    seats: int
    is_active: bool

class VehicleCreate(VehicleBase):
    pass

class VehicleUpdate(VehicleBase):
    pass