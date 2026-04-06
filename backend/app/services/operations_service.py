from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.operations import Request, Assignment, RequestStatus
from app.schemas.operations import RequestCreate, AssignmentCreate

async def create_request(db: AsyncSession, request_in: RequestCreate, farmer_id: int) -> Request:
    # Baseline logic, priority score matching engine to be built here later
    db_obj = Request(
        **request_in.model_dump(), 
        farmer_id=farmer_id,
        priority_score=0.0
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_requests_by_farmer(db: AsyncSession, farmer_id: int):
    query = select(Request).where(Request.farmer_id == farmer_id)
    result = await db.execute(query)
    return result.scalars().all()

async def get_all_pending_requests(db: AsyncSession):
    query = select(Request).where(Request.status == RequestStatus.PENDING).order_by(Request.priority_score.desc())
    result = await db.execute(query)
    return result.scalars().all()

async def create_assignment(db: AsyncSession, assign_in: AssignmentCreate) -> Assignment:
    db_obj = Assignment(**assign_in.model_dump())
    db.add(db_obj)
    
    # Automatically update the source Request status
    req_result = await db.execute(select(Request).where(Request.id == assign_in.request_id))
    req = req_result.scalar_one_or_none()
    if req:
        req.status = RequestStatus.ASSIGNED
        
    await db.commit()
    await db.refresh(db_obj)
    return db_obj
