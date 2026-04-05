from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
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

    owner = relationship("User", backref="machines")

class LabourTeam(Base):
    __tablename__ = "labour_teams"

    id = Column(Integer, primary_key=True, index=True)
    leader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    worker_count = Column(Integer, nullable=False)
    skills = Column(String, nullable=False) # Simple comma-separated for MVP
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    leader = relationship("User", backref="labour_teams")
