from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.farm import Farm
from app.models.operations import Request, Assignment
from app.schemas.farm import FarmCreate
from app.core.exceptions import AgriFluxException

async def create_farm(db: AsyncSession, farm_in: FarmCreate, farmer_id: int) -> Farm:
    db_obj = Farm(**farm_in.model_dump(), farmer_id=farmer_id)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    
    from app.services.notification_service import notification_manager
    await notification_manager.notify_admins(
        event_type="FARM_CREATED",
        entity_type="farm",
        entity_id=db_obj.id,
        message=f"New farm operation registered: {db_obj.name}"
    )
    await notification_manager.notify_user(
        target_user_id=farmer_id,
        event_type="FARM_CREATED",
        entity_type="farm",
        entity_id=db_obj.id,
        message=f"Farm Registered: {db_obj.name}"
    )
    
    return db_obj

async def get_farms_by_farmer(db: AsyncSession, farmer_id: int):
    query = select(Farm).where(Farm.farmer_id == farmer_id)
    result = await db.execute(query)
    return result.scalars().all()

async def get_all_farms(db: AsyncSession):
    query = select(Farm)
    result = await db.execute(query)
    return result.scalars().all()

async def delete_farm(db: AsyncSession, farm_id: int, farmer_id: int, confirm: bool = False):
    if not confirm:
        raise AgriFluxException("System safety lock engaged. Explicit confirmation required to purge target.", status_code=400)
    
    # 1. Fetch farm and ensure ownership
    query = select(Farm).where(Farm.id == farm_id)
    result = await db.execute(query)
    farm = result.scalar_one_or_none()
    
    if not farm:
        raise AgriFluxException("Target farm not found in sector.", status_code=404)
        
    if farm.farmer_id != farmer_id:
        raise AgriFluxException("Access Denied: You do not have clearance for this operation.", status_code=403)
    
    # 2. Check for active assignments (RESTRICT behavior)
    # Any assignment with status 'SCHEDULED' blocks deletion.
    active_q = select(Assignment).join(Request).where(Request.farm_id == farm_id).where(Assignment.status == 'SCHEDULED')
    active_res = await db.execute(active_q)
    if active_res.first():
        raise AgriFluxException("Critical Conflict: Target farm has active logistical commitments. Purge restricted.", status_code=400)
    
    # 3. Perform Cascade Delete
    # Note: SQLAlchemy cascade 'all, delete-orphan' handles Request and Assignment removal.
    farm_name = farm.name
    await db.delete(farm)
    await db.commit()
    
    from app.services.notification_service import notification_manager
    await notification_manager.notify_admins(
        event_type="FARM_DELETED",
        entity_type="farm",
        entity_id=farm_id,
        message=f"Farm operation purged: {farm_name}"
    )
    await notification_manager.notify_user(
        target_user_id=farmer_id,
        event_type="FARM_DELETED",
        entity_type="farm",
        entity_id=farm_id,
        message=f"Farm operation purged: {farm_name}"
    )
    
    return True
