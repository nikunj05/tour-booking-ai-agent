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
    country_code = Column(String(10), nullable=False, server_default='+91')
    phone = Column(String(20))
    status = Column(String(20), default="active")
    currency = Column(String(10), default="USD")
    country = Column(String(100))
    
    whatsapp_access_token = Column(String(255), nullable=True)
    whatsapp_phone_number_id = Column(String(50), nullable=True)
    whatsapp_business_account_id = Column(String(50), nullable=True)
    whatsapp_template_lang = Column(String(10), default="en_US")
    whatsapp_webhook_verify_token = Column(String(50), nullable=True)

    stripe_publishable_key = Column(String(255), nullable=True)
    stripe_secret_key = Column(String(255), nullable=True)
    stripe_webhook_secret = Column(String(255), nullable=True)
    is_deleted = Column(Boolean, default=False)


    user = relationship("User", back_populates="company")
    tour_packages = relationship(
        "TourPackage",
        back_populates="company",
        cascade="all, delete-orphan"
    )

    customers = relationship(
        "Customer",
        back_populates="company",
        cascade="all, delete-orphan"
    )

    chat_sessions = relationship(
        "ChatSession",
        back_populates="company",
        cascade="all, delete-orphan"
    )


