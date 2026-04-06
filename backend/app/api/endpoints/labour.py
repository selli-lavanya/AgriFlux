from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.database import get_db
from app.schemas.resource import LabourTeamCreate, LabourTeamOut
from app.services import resource_service
from app.api.deps import RoleChecker
from app.models.user import User, UserRole

router = APIRouter()

labour_only = RoleChecker([UserRole.LABOUR_TEAM, UserRole.ADMIN])

@router.post("/", response_model=LabourTeamOut)
async def create_new_labour_team(
    team_in: LabourTeamCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(labour_only)
):
    return await resource_service.create_labour_team(db, team_in=team_in, leader_id=current_user.id)

@router.get("/", response_model=List[LabourTeamOut])
async def read_my_labour_teams(
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(labour_only)
):
    return await resource_service.get_labour_teams_by_leader(db, leader_id=current_user.id)
