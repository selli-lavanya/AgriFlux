from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.database import get_db
from app.schemas.farm import FarmCreate, FarmOut
from app.services import farm_service
from app.api.deps import RoleChecker
from app.models.user import User, UserRole

router = APIRouter()

farmer_only = RoleChecker([UserRole.FARMER, UserRole.ADMIN])

@router.post("/", response_model=FarmOut)
async def create_new_farm(
    farm_in: FarmCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(farmer_only)
):
    return await farm_service.create_farm(db, farm_in=farm_in, farmer_id=current_user.id)

@router.get("/", response_model=List[FarmOut])
async def read_my_farms(
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(farmer_only)
):
    return await farm_service.get_farms_by_farmer(db, farmer_id=current_user.id)

@router.get("/all", response_model=List[FarmOut])
async def read_all_farms(
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(RoleChecker([UserRole.ADMIN]))
):
    return await farm_service.get_all_farms(db)

@router.delete("/{farm_id}")
async def delete_farm_operation(
    farm_id: int,
    confirm: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(farmer_only)
):
    await farm_service.delete_farm(db, farm_id=farm_id, farmer_id=current_user.id, confirm=confirm)
    return {"status": "purged", "message": "Territory and associated logistics purged from Matrix."}
