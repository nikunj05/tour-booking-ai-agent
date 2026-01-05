# app/models/agent.py
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from app.database.base import Base
from sqlalchemy.orm import relationship


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    company_name = Column(String(150), nullable=False)
    logo = Column(String(255), nullable=True)  
    phone = Column(String(20))
    status = Column(String(20), default="active")
    is_deleted = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="agent")


