from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base

class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False) # e.g., Harvester, Tractor
    capacity_per_day = Column(Float, nullable=False) # e.g., acres per day
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Phase 1 / 1b additions
    status = Column(String, nullable=False, server_default='active')
    cooldown_until = Column(DateTime(timezone=True), nullable=True)
    daily_failure_count = Column(Integer, nullable=False, server_default='0')
    daily_no_show_count = Column(Integer, nullable=False, server_default='0')
    failure_count = Column(Integer, nullable=False, server_default='0')
    no_show_count = Column(Integer, nullable=False, server_default='0')
    late_cancel_count = Column(Integer, nullable=False, server_default='0')
    penalty_count = Column(Integer, nullable=False, server_default='0')
    avg_speed = Column(Float, nullable=False, server_default='40.0')
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    cost_per_hour = Column(Float, nullable=False, server_default='150.0')
    last_infraction_date = Column(Date, nullable=True)

    owner = relationship("User", backref="machines")

class LabourTeam(Base):
    __tablename__ = "labour_teams"

    id = Column(Integer, primary_key=True, index=True)
    leader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    worker_count = Column(Integer, nullable=False)
    skills = Column(String, nullable=False) # Simple comma-separated for MVP
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Phase 1 / 1b additions
    status = Column(String, nullable=False, server_default='active')
    cooldown_until = Column(DateTime(timezone=True), nullable=True)
    daily_failure_count = Column(Integer, nullable=False, server_default='0')
    daily_no_show_count = Column(Integer, nullable=False, server_default='0')
    failure_count = Column(Integer, nullable=False, server_default='0')
    no_show_count = Column(Integer, nullable=False, server_default='0')
    late_cancel_count = Column(Integer, nullable=False, server_default='0')
    penalty_count = Column(Integer, nullable=False, server_default='0')
    avg_speed = Column(Float, nullable=False, server_default='40.0')
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    cost_per_worker_per_hour = Column(Float, nullable=False, server_default='50.0')
    last_infraction_date = Column(Date, nullable=True)

    leader = relationship("User", backref="labour_teams")

