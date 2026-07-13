from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean
from sqlalchemy.sql import func
from app.db.database import Base

class AvailabilityCalendar(Base):
    __tablename__ = "availability_calendar"

    id = Column(Integer, primary_key=True, index=True)
    resource_type = Column(String, nullable=False) # 'machine' or 'labour'
    resource_id = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    status = Column(String, nullable=False) # 'available', 'booked'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Phase 1b additions
    temp_lock_until = Column(DateTime(timezone=True), nullable=True)
    locked_by_request_id = Column(Integer, nullable=True)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    type = Column(String, nullable=False) # weather, bottleneck, system
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
