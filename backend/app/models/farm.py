from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base

class Farm(Base):
    __tablename__ = "farms"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    size_acres = Column(Float, nullable=False)
    location_lat = Column(Float, nullable=False)
    location_lng = Column(Float, nullable=False)
    location_label = Column(String, nullable=True)
    full_address = Column(String, nullable=True)
    crop_type = Column(String, nullable=False)
    crop_stage = Column(String, nullable=False)  # MVP: manually entered stage
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    farmer = relationship("User", backref="farms")
