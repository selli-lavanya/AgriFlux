from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.database import get_db
from app.schemas.operations import RequestCreate, RequestOut
from app.services import operations_service
from app.services.priority_engine import priority_engine
from app.api.deps import RoleChecker
from app.models.user import User, UserRole

router = APIRouter()

farmer_only = RoleChecker([UserRole.FARMER, UserRole.ADMIN])
admin_only = RoleChecker([UserRole.ADMIN])

@router.post("/", response_model=RequestOut)
async def submit_request(
    request_in: RequestCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(farmer_only)
):
    return await operations_service.create_request(db, request_in=request_in, farmer_id=current_user.id)

@router.get("/me", response_model=List[RequestOut])
async def list_my_requests(
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(farmer_only)
):
    return await operations_service.get_requests_by_farmer(db, farmer_id=current_user.id)

@router.get("/pending", response_model=List[RequestOut])
async def list_pending_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    return await operations_service.get_all_pending_requests(db)

@router.post("/trigger-engine")
async def manual_trigger_priority_engine(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Admin endpoint to manually spin up the Risk Evaluation Engine."""
    return await priority_engine.evaluate_pending_requests(db)
