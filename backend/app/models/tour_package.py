from sqlalchemy import (
    Column, Integer, String, Text, Float,
    Boolean, ForeignKey, Enum
)
from sqlalchemy.orm import relationship
from app.database.base import Base


class TourPackage(Base):
    __tablename__ = "tour_packages"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    country = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)

    itinerary = Column(Text, nullable=True)
    excludes = Column(Text, nullable=True)

    status = Column(String(20), default="active")  # active | inactive

    is_deleted = Column(Boolean, default=False)

    agent = relationship("Agent", back_populates="tour_packages")
    gallery_images = relationship(
        "TourPackageGalleryImage",
        back_populates="tour_package",
        cascade="all, delete-orphan"
    )


class TourPackageGalleryImage(Base):
    __tablename__ = "tour_package_gallery_images"

    id = Column(Integer, primary_key=True, index=True)
    tour_package_id = Column(
        Integer,
        ForeignKey("tour_packages.id", ondelete="CASCADE"),
        nullable=False
    )

    image_path = Column(String(255), nullable=False)
    image_type = Column(String(20), nullable=False)  # cover | gallery

    tour_package = relationship("TourPackage", back_populates="gallery_images")
