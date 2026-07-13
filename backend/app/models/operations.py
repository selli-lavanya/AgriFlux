from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base

class RequestType(str, Enum):
    MACHINE = "machine"
    LABOUR = "labour"
    IRRIGATION = "irrigation"

class RequestStatus(str, Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    UNSERVICED = "UNSERVICED"

class AssignmentStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    CANCELLED = "CANCELLED"
    LATE_CANCEL = "LATE_CANCEL"
    FAILED = "FAILED"
    NO_SHOW = "NO_SHOW"
    COMPLETED = "COMPLETED"

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

    # Phase 1 / 1b additions
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Integer, nullable=True)  # in minutes
    max_budget_per_hour = Column(Float, nullable=True)
    max_total_budget = Column(Float, nullable=True)
    work_size = Column(Float, nullable=True)
    quantity = Column(Integer, nullable=True)
    workers_required = Column(Integer, nullable=True)
    partial_allowed = Column(Boolean, nullable=False, server_default='false')
    reassignment_attempts = Column(Integer, nullable=False, server_default='0')
    estimated_cost = Column(Float, nullable=True)

    farmer = relationship("User", backref="requests")
    farm = relationship("Farm", back_populates="requests")
    assignments = relationship("Assignment", back_populates="request", cascade="all, delete-orphan")

class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False)
    resource_type = Column(String, nullable=False) # 'machine' or 'labour'
    resource_id = Column(Integer, nullable=False)  # Generic ID mapping
    scheduled_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(SQLEnum(AssignmentStatus, native_enum=False), default=AssignmentStatus.SCHEDULED)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Phase 1 / 1b additions
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Integer, nullable=True)  # in minutes
    workers_assigned = Column(Integer, nullable=False, server_default='1')
    final_cost = Column(Float, nullable=True)
    cancelled_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(String, nullable=True)
    is_late_cancel = Column(Boolean, nullable=False, server_default='false')
    failure_logged = Column(Boolean, nullable=False, server_default='false')

    request = relationship("Request", back_populates="assignments")
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])

