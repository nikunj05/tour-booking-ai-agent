from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    ForeignKey,
    Date,
    Time,
    Numeric,
    DateTime
)
from sqlalchemy.sql import func
from app.database.base import Base
from sqlalchemy.orm import relationship

class ManualBooking(Base):
    __tablename__ = "manual_bookings"

    id = Column(Integer, primary_key=True, index=True)
    guest_name = Column(String(150), nullable=True)
    country_code = Column(String(10), nullable=True, server_default='+91')
    phone = Column(String(20), nullable=True)
    email = Column(String(150), nullable=True)
    adults = Column(Integer, nullable=False, default=1)
    kids = Column(Integer, nullable=False, default=0)
    tour_package_id = Column(
        Integer,
        ForeignKey("tour_packages.id"),
        nullable=False
    )
    driver_id = Column(
        Integer,
        ForeignKey("drivers.id"),
        nullable=True    
    )
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    travel_date = Column(Date, nullable=False)
    travel_time = Column(Time, nullable=True)
    total_amount = Column(Numeric(10, 2), nullable=False)
    advance_amount = Column(Numeric(10, 2), default=0)
    remaining_amount = Column(Numeric(10, 2), default=0)
    pickup_location = Column(String(255), nullable=True)
    payment_status = Column(
        String(20),
        default="pending"
    ) 
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tour_package = relationship("TourPackage")
    driver = relationship("Driver", back_populates="bookings")
    customer = relationship("Customer", back_populates="bookings")
