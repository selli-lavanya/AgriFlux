from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.database import get_db
from app.schemas.operations import AssignmentCreate, AssignmentOut
from app.services import operations_service
from app.api.deps import RoleChecker
from app.models.user import User, UserRole

router = APIRouter()

admin_only = RoleChecker([UserRole.ADMIN])

@router.post("/", response_model=AssignmentOut)
async def dispatch_assignment(
    assignment_in: AssignmentCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(admin_only)
):
    return await operations_service.create_assignment(db, assign_in=assignment_in)
