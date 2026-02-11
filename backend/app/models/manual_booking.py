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
    adults = Column(Integer, nullable=False, default=1)
    kids = Column(Integer, nullable=False, default=0)
    tour_package_id = Column(
        Integer,
        ForeignKey("tour_packages.id"),
        nullable=False
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
    payment_ref = Column(String(255), nullable=True)
    transport_type = Column(String(20), nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tour_package = relationship("TourPackage")
    customer = relationship("Customer", back_populates="bookings")
    vehicles_drivers = relationship("BookingVehicleDriver", back_populates="booking", cascade="all, delete-orphan")

class BookingVehicleDriver(Base):
    __tablename__ = "booking_vehicle_drivers"

    id = Column(Integer, primary_key=True, index=True)

    booking_id = Column(
        Integer,
        ForeignKey("manual_bookings.id", ondelete="CASCADE"),
        nullable=False
    )

    vehicle_id = Column(
        Integer,
        ForeignKey("vehicles.id"),
        nullable=True
    )

    driver_id = Column(
        Integer,
        ForeignKey("drivers.id"),
        nullable=True
    )

    seats = Column(Integer, nullable=True)  # optional seats for this assignment

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    booking = relationship("ManualBooking", back_populates="vehicles_drivers")
    vehicle = relationship("Vehicle")
    driver = relationship("Driver")