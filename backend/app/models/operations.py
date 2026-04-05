from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base

class RequestType(str, Enum):
    MACHINE = "machine"
    LABOUR = "labour"
    IRRIGATION = "irrigation"

class RequestStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    type = Column(SQLEnum(RequestType), nullable=False)
    required_by_date = Column(DateTime(timezone=True), nullable=False)
    
    # Priority engine results
    priority_score = Column(Float, default=0.0)
    priority_reason = Column(String, nullable=True)
    
    status = Column(SQLEnum(RequestStatus), default=RequestStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    farmer = relationship("User", backref="requests")
    farm = relationship("Farm", backref="requests")

class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False)
    resource_type = Column(String, nullable=False) # 'machine' or 'labour'
    resource_id = Column(Integer, nullable=False)  # Generic ID mapping
    scheduled_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, default="scheduled")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    request = relationship("Request", backref="assignments")
