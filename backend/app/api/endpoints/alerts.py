from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.db.database import get_db
from app.schemas.alert import AlertOut
from app.models.availability import Alert
from app.models.user import User
from app.api.deps import get_current_active_user

router = APIRouter()

@router.get("/", response_model=List[AlertOut])
async def get_my_alerts(
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    query = select(Alert).where(Alert.user_id == current_user.id).order_by(Alert.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()
