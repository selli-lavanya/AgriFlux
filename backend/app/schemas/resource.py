from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional

class MachineBase(BaseModel):
    type: str
    capacity_per_day: float
    avg_speed: Optional[float] = 40.0
    lat: Optional[float] = None
    lng: Optional[float] = None
    cost_per_hour: Optional[float] = 150.0

class MachineCreate(MachineBase):
    pass

class MachineOut(MachineBase):
    id: int
    owner_id: int
    created_at: datetime
    status: str
    cooldown_until: Optional[datetime] = None
    daily_failure_count: int
    daily_no_show_count: int
    failure_count: int
    no_show_count: int
    late_cancel_count: int
    penalty_count: int
    last_infraction_date: Optional[date] = None

    class Config:
        from_attributes = True

class LabourTeamBase(BaseModel):
    worker_count: int
    skills: str
    avg_speed: Optional[float] = 40.0
    lat: Optional[float] = None
    lng: Optional[float] = None
    cost_per_worker_per_hour: Optional[float] = 50.0

class LabourTeamCreate(LabourTeamBase):
    pass

class LabourTeamOut(LabourTeamBase):
    id: int
    leader_id: int
    created_at: datetime
    status: str
    cooldown_until: Optional[datetime] = None
    daily_failure_count: int
    daily_no_show_count: int
    failure_count: int
    no_show_count: int
    late_cancel_count: int
    penalty_count: int
    last_infraction_date: Optional[date] = None

    class Config:
        from_attributes = True

