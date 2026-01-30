from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Boolean, Text
from sqlalchemy.ext.mutable import MutableDict
from app.database.base import Base
from datetime import datetime
from sqlalchemy.orm import relationship

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)  
    phone = Column(String(20), index=True, nullable=False)
    state = Column(String(50), default="greeting")  

    data = Column(MutableDict.as_mutable(JSON), default=dict)
    context = Column(MutableDict.as_mutable(JSON), default=dict)

    last_message_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
                
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="chat_sessions")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True)

    session_id = Column(Integer, ForeignKey("chat_sessions.id"), index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))

    sender = Column(String(10))  
    message_type = Column(String(20), default="text") 
    message = Column(Text)

    whatsapp_message_id = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)