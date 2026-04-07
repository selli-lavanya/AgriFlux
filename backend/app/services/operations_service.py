from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.operations import Request, Assignment, RequestStatus
from app.schemas.operations import RequestCreate, AssignmentCreate
from fastapi import HTTPException
from sqlalchemy import func, cast, Date

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
    # Phase 14: Conflict Engine Check
    target_date = assign_in.scheduled_date.date()
    conflict_query = select(Assignment).where(
        Assignment.resource_type == assign_in.resource_type,
        Assignment.resource_id == assign_in.resource_id,
        cast(Assignment.scheduled_date, Date) == target_date,
        Assignment.status != 'completed'
    )
    result = await db.execute(conflict_query)
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Conflict Detected: Assuring Zero Collisions - Resource is already heavily assigned on this exact terrestrial date!")

    db_obj = Assignment(**assign_in.model_dump())
    db.add(db_obj)
    
    # Automatically update the source Request status
    req_result = await db.execute(select(Request).where(Request.id == assign_in.request_id))
    req = req_result.scalar_one_or_none()
    if req:
        req.status = RequestStatus.ASSIGNED
        
    await db.commit()
    await db.refresh(db_obj)
    await db.refresh(db_obj)
    return db_obj

async def get_assignments_for_provider(db: AsyncSession, user_id: int, role: str):
    from app.models.resource import Machine, LabourTeam
    if role == 'machine_owner':
        res = await db.execute(select(Machine.id).where(Machine.owner_id == user_id))
        m_ids = res.scalars().all()
        if not m_ids: return []
        q = select(Assignment).where(Assignment.resource_type == 'machine', Assignment.resource_id.in_(m_ids))
        res2 = await db.execute(q)
        return res2.scalars().all()
    elif role == 'labour_team':
        res = await db.execute(select(LabourTeam.id).where(LabourTeam.leader_id == user_id))
        l_ids = res.scalars().all()
        if not l_ids: return []
        q = select(Assignment).where(Assignment.resource_type == 'labour', Assignment.resource_id.in_(l_ids))
        res2 = await db.execute(q)
        return res2.scalars().all()
    return []

async def complete_assignment(db: AsyncSession, assignment_id: int):
    res = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    assign = res.scalar_one_or_none()
    if not assign: return None
    
    # Mark task completed
    assign.status = 'completed'
    
    # Cascade mark original request completed
    req_res = await db.execute(select(Request).where(Request.id == assign.request_id))
    req = req_res.scalar_one_or_none()
    if req:
        req.status = RequestStatus.COMPLETED
        
    await db.commit()
    return assign
