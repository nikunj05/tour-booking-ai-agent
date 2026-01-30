from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database.base import Base
from datetime import datetime

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    guest_name = Column(String(150), nullable=False)
    country_code = Column(String(10), nullable=False, server_default='+91')
    phone = Column(String(20), nullable=False)
    email = Column(String(150), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)

    company = relationship("Company", back_populates="customers")
    bookings = relationship("ManualBooking", back_populates="customer")
