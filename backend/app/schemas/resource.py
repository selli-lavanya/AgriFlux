from pydantic import BaseModel
from datetime import datetime

class MachineBase(BaseModel):
    type: str
    capacity_per_day: float

class MachineCreate(MachineBase):
    pass

class MachineOut(MachineBase):
    id: int
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class LabourTeamBase(BaseModel):
    worker_count: int
    skills: str

class LabourTeamCreate(LabourTeamBase):
    pass

class LabourTeamOut(LabourTeamBase):
    id: int
    leader_id: int
    created_at: datetime

    class Config:
        from_attributes = True
