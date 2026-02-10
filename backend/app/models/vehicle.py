from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    vehicle_type = Column(String, nullable=True)   
    vehicle_number = Column(String, nullable=True)
    seats = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)

    # Relationship to multiple photos
    company = relationship("Company", backref="vehicles")
    photos = relationship("VehiclePhoto", back_populates="vehicle", cascade="all, delete-orphan")

class VehiclePhoto(Base):
    __tablename__ = "vehicle_photos"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"))
    file_path = Column(String, nullable=False)

    vehicle = relationship("Vehicle", back_populates="photos")
