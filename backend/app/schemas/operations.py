from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.operations import RequestType, RequestStatus, AssignmentStatus

class RequestBase(BaseModel):
    farm_id: int
    type: RequestType
    required_by_date: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    max_budget_per_hour: Optional[float] = None
    max_total_budget: Optional[float] = None
    work_size: Optional[float] = None
    quantity: Optional[int] = None
    workers_required: Optional[int] = None
    partial_allowed: bool = False

class RequestCreate(RequestBase):
    pass

class RequestOut(RequestBase):
    id: int
    farmer_id: int
    status: RequestStatus
    priority_score: float
    priority_reason: Optional[str] = None
    reassignment_attempts: int
    estimated_cost: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AssignmentBase(BaseModel):
    request_id: int
    resource_type: str
    resource_id: int
    scheduled_date: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    workers_assigned: int = 1
    final_cost: Optional[float] = None

class AssignmentCreate(AssignmentBase):
    pass

class AssignmentOut(AssignmentBase):
    id: int
    status: AssignmentStatus
    cancelled_by_id: Optional[int] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    is_late_cancel: bool = False
    failure_logged: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

