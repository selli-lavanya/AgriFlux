from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class FarmBase(BaseModel):
    name: str
    size_acres: float
    location_lat: float
    location_lng: float
    location_label: Optional[str] = None
    full_address: Optional[str] = None
    crop_type: str
    crop_stage: str

class FarmCreate(FarmBase):
    pass

class FarmUpdate(BaseModel):
    name: Optional[str] = None
    size_acres: Optional[float] = None
    crop_stage: Optional[str] = None

class FarmOut(FarmBase):
    id: int
    farmer_id: int
    created_at: datetime

    class Config:
        from_attributes = True
