# app/models/company.py
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from app.database.base import Base
from sqlalchemy.orm import relationship


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    company_name = Column(String(150), nullable=False)
    logo = Column(String(255), nullable=True)  
    phone = Column(String(20))
    status = Column(String(20), default="active")
    currency = Column(String(10), default="USD")
    country = Column(String(100))
    is_deleted = Column(Boolean, default=False)


    user = relationship("User", back_populates="company")
    tour_packages = relationship(
        "TourPackage",
        back_populates="company",
        cascade="all, delete-orphan"
    )


