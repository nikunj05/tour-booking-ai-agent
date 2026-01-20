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
    guest_name = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(150), nullable=True)
    tour_package_id = Column(
        Integer,
        ForeignKey("tour_packages.id"),
        nullable=False
    )
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
