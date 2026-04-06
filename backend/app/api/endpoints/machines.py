from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.database import get_db
from app.schemas.resource import MachineCreate, MachineOut
from app.services import resource_service
from app.api.deps import RoleChecker
from app.models.user import User, UserRole

router = APIRouter()

machine_owner_only = RoleChecker([UserRole.MACHINE_OWNER, UserRole.ADMIN])

@router.post("/", response_model=MachineOut)
async def create_new_machine(
    machine_in: MachineCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(machine_owner_only)
):
    return await resource_service.create_machine(db, machine_in=machine_in, owner_id=current_user.id)

@router.get("/", response_model=List[MachineOut])
async def read_my_machines(
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(machine_owner_only)
):
    return await resource_service.get_machines_by_owner(db, owner_id=current_user.id)
