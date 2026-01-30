from pydantic import BaseModel, EmailStr
from datetime import date, time
from typing import Optional


class ManualBookingCreate(BaseModel):
    guest_name: str
    country_code: str
    phone: str
    email: Optional[EmailStr] = None
    pickup_location: Optional[str] = None
    tour_package_id: int
    travel_date: date
    travel_time: Optional[time] = None
    total_amount: float
    advance_amount: float = 0


class ManualBookingUpdate(BaseModel):
    guest_name: str
    country_code: str
    phone: str
    email: Optional[EmailStr] = None
    pickup_location: Optional[str] = None
    travel_date: date
    travel_time: Optional[time] = None
    total_amount: float
    advance_amount: float


class ManualBookingOut(BaseModel):
    id: int
    guest_name: str
    country_code: str
    phone: str
    email: Optional[EmailStr]
    pickup_location: Optional[str]
    travel_date: date
    travel_time: Optional[time]
    total_amount: float
    advance_amount: float
    remaining_amount: float
    payment_status: str

    class Config:
        from_attributes = True
