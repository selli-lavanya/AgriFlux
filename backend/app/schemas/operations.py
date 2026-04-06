from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.operations import RequestType, RequestStatus

class RequestBase(BaseModel):
    farm_id: int
    type: RequestType
    required_by_date: datetime

class RequestCreate(RequestBase):
    pass

class RequestOut(RequestBase):
    id: int
    farmer_id: int
    status: RequestStatus
    priority_score: float
    priority_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AssignmentBase(BaseModel):
    request_id: int
    resource_type: str
    resource_id: int
    scheduled_date: datetime

class AssignmentCreate(AssignmentBase):
    pass

class AssignmentOut(AssignmentBase):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
