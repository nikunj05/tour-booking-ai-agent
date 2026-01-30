from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name = Column(String, nullable=False)
    country_code = Column(String(10), nullable=False, server_default='+91')
    phone_number = Column(String, nullable=False)
    vehicle_type = Column(String, nullable=True)   
    vehicle_number = Column(String, nullable=True)
    seats = Column(Integer, nullable=True)
    image = Column(String, nullable=True)
    is_deleted = Column(Boolean, default=False)
    company = relationship("Company", backref="drivers")

    tour_packages = relationship(
        "TourPackageDriver",
        back_populates="driver",
        cascade="all, delete-orphan"
    )

    bookings = relationship("ManualBooking", back_populates="driver")
