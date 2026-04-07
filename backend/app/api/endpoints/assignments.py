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
providers_only = RoleChecker([UserRole.MACHINE_OWNER, UserRole.LABOUR_TEAM])

@router.post("/", response_model=AssignmentOut)
async def dispatch_assignment(
    assignment_in: AssignmentCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(admin_only)
):
    return await operations_service.create_assignment(db, assign_in=assignment_in)

@router.get("/my-tasks", response_model=List[AssignmentOut])
async def get_my_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(providers_only)
):
    return await operations_service.get_assignments_for_provider(db, current_user.id, current_user.role)

@router.put("/{assignment_id}/complete", response_model=AssignmentOut)
async def complete_task(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(providers_only)
):
    return await operations_service.complete_assignment(db, assignment_id)
