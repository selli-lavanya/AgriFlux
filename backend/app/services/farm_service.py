from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.farm import Farm
from app.schemas.farm import FarmCreate

async def create_farm(db: AsyncSession, farm_in: FarmCreate, farmer_id: int) -> Farm:
    db_obj = Farm(**farm_in.model_dump(), farmer_id=farmer_id)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_farms_by_farmer(db: AsyncSession, farmer_id: int):
    query = select(Farm).where(Farm.farmer_id == farmer_id)
    result = await db.execute(query)
    return result.scalars().all()

async def get_all_farms(db: AsyncSession):
    query = select(Farm)
    result = await db.execute(query)
    return result.scalars().all()
