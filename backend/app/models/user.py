from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from app.db.database import Base

class UserRole(str, Enum):
    FARMER = "farmer"
    MACHINE_OWNER = "machine_owner"
    LABOUR_TEAM = "labour_team"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Phase 1 additions
    late_cancel_count = Column(Integer, nullable=False, server_default='0')
    no_show_count = Column(Integer, nullable=False, server_default='0')

