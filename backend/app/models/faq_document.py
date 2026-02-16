from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.base import Base
from pgvector.sqlalchemy import Vector


class FAQDocument(Base):
    __tablename__ = "faq_documents"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    embedding = Column(Vector(1536), nullable=True)
    
    company = relationship("Company", back_populates="faq_documents")
