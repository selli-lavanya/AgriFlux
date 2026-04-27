from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.operations import Request, Assignment, RequestStatus
from app.schemas.operations import RequestCreate, AssignmentCreate
from fastapi import HTTPException
from sqlalchemy import func, cast, Date
from app.services.notification_service import notification_manager

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
    
    # Fetch farm name for admin clarity
    from app.models.farm import Farm
    farm_res = await db.execute(select(Farm).where(Farm.id == db_obj.farm_id))
    farm = farm_res.scalar_one_or_none()
    farm_name = f"{farm.name} ({farm.location_label})" if farm and farm.location_label else (farm.name if farm else f"Farm #{db_obj.farm_id}")
    work_date = db_obj.required_by_date.strftime("%d %b")
    
    # Notify Admins dynamically about fresh incoming demand
    priority_flag = "⚠️ " if db_obj.priority_score > 50 else ""
    await notification_manager.notify_admins(
        event_type="NEW_REQUEST",
        entity_type="req",
        entity_id=db_obj.id,
        message=f"{priority_flag}New {db_obj.type.capitalize()} needed for {farm_name}. Target Work Date: {work_date}"
    )
    
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
    from app.core.exceptions import AgriFluxException
    try:
        # Phase 14 & 18: Robust Conflict Engine Check (PostgreSQL/SQLite Compatible)
        target_date = assign_in.scheduled_date.date()
        conflict_query = select(Assignment).where(
            Assignment.resource_type == assign_in.resource_type,
            Assignment.resource_id == assign_in.resource_id,
            cast(Assignment.scheduled_date, Date) == target_date,
            Assignment.status != 'completed'
        )
        result = await db.execute(conflict_query)
        existing_assignment = result.scalars().first()
        
        if existing_assignment:
            raise AgriFluxException(
                message=f"Conflict Detected: Resource #{assign_in.resource_id} ({assign_in.resource_type}) is already committed on {target_date}.",
                status_code=400
            )

        db_obj = Assignment(**assign_in.model_dump())
        db.add(db_obj)
        
        # Automatically update the source Request status
        req_result = await db.execute(select(Request).where(Request.id == assign_in.request_id))
        req = req_result.scalar_one_or_none()
        if req:
            req.status = RequestStatus.ASSIGNED
            
        await db.commit()
        await db.refresh(db_obj)
        
        # Notify source Farmer that their request is actively fulfilled
        if req:
            from app.models.farm import Farm
            farm_res = await db.execute(select(Farm).where(Farm.id == req.farm_id))
            farm = farm_res.scalar_one_or_none()
            farm_name = f"{farm.name} ({farm.location_label})" if farm and farm.location_label else (farm.name if farm else "Your Farm")
            
            # Ensure required_by_date is a datetime object
            work_date = req.required_by_date
            if isinstance(work_date, str):
                from datetime import datetime
                work_date = datetime.fromisoformat(work_date.replace('Z', '+00:00'))
            
            date_str = work_date.strftime("%d %b")
            msg = f"{assign_in.resource_type.capitalize()} assigned for {farm_name}\nWork Date: {date_str}\nStatus: Scheduled"
            
            # Notify Farmer
            await notification_manager.notify_user(
                target_user_id=req.farmer_id,
                event_type="ASSIGNMENT_CREATED",
                entity_type="req",
                entity_id=req.id,
                message=msg
            )
            
            # Phase 18: Also notify Admins so their Dispatcher and Matrix sync instantly
            await notification_manager.notify_admins(
                event_type="ASSIGNMENT_CREATED",
                entity_type="req",
                entity_id=req.id,
                message=f"ASSIGNMENT SYNC: {msg}"
            )
        
        return db_obj
    except AgriFluxException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Assignment Engine Error: {str(e)}", exc_info=True)
        raise AgriFluxException(
            message="Assignment Engine Failure",
            details=f"An internal error occurred while processing the match: {str(e)}",
            status_code=500
        )

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
    
    # Phase 17 Notification Hook: End of loop
    if req:
        from app.models.farm import Farm
        farm_res = await db.execute(select(Farm).where(Farm.id == req.farm_id))
        farm = farm_res.scalar_one_or_none()
        farm_name = f"{farm.name} ({farm.location_label})" if farm and farm.location_label else (farm.name if farm else "Your Farm")
        
        msg = f"Work completed for {farm_name}\n{assign.resource_type.capitalize()} task finished successfully"
        
        # Notify Farmer
        await notification_manager.notify_user(
            target_user_id=req.farmer_id,
            event_type="ASSIGNMENT_COMPLETED",
            entity_type="req",
            entity_id=req.id,
            message=msg
        )
        
        # Notify Admins for real-time status sync
        await notification_manager.notify_admins(
            event_type="ASSIGNMENT_COMPLETED",
            entity_type="req",
            entity_id=req.id,
            message=f"COMPLETION SYNC: {msg}"
        )
        
    return assign
