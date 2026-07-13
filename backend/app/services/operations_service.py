import math
from typing import Optional
from datetime import datetime, timezone, timedelta
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, cast, Date, delete, text
from app.models.operations import Request, Assignment, RequestStatus, AssignmentStatus, RequestType
from app.models.resource import Machine, LabourTeam
from app.models.user import User
from app.models.farm import Farm
from app.models.availability import AvailabilityCalendar
from app.schemas.operations import RequestCreate, AssignmentCreate
from app.services.notification_service import notification_manager
from app.db.database import AsyncSessionLocal

async def create_request(
    db: AsyncSession,
    request_in: RequestCreate,
    farmer_id: int,
    background_tasks: Optional[BackgroundTasks] = None
) -> Request:
    from app.core.exceptions import AgriFluxException
    
    # Ensure target date is not in the past (allow today)
    if request_in.required_by_date.date() < datetime.now(timezone.utc).date():
        raise AgriFluxException("Invalid parameter: Cannot deploy requests for past dates.", status_code=400)
        
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
        message=f"{priority_flag}{db_obj.type.capitalize()} requested for {farm_name} for {work_date}"
    )
    
    if background_tasks:
        trigger_assignment_engine(background_tasks)
        
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
    from datetime import datetime, timezone
    try:
        # Phase 14 & 18: Robust Conflict Engine Check (PostgreSQL/SQLite Compatible)
        target_date = assign_in.scheduled_date.date()
        
        # Prevent assignment for past dates
        if target_date < datetime.now(timezone.utc).date():
            raise AgriFluxException("Invalid parameter: Cannot deploy assignments for past dates.", status_code=400)
            
        conflict_query = select(Assignment).where(
            Assignment.resource_type == assign_in.resource_type,
            Assignment.resource_id == assign_in.resource_id,
            cast(Assignment.scheduled_date, Date) == target_date,
            Assignment.status != AssignmentStatus.COMPLETED
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
            
            # Fetch dynamic resource name
            resource_name = assign_in.resource_type.capitalize()
            if assign_in.resource_type == 'machine':
                from app.models.resource import Machine
                m_res = await db.execute(select(Machine).where(Machine.id == assign_in.resource_id))
                m = m_res.scalar_one_or_none()
                if m: resource_name = m.type
            elif assign_in.resource_type == 'labour':
                from app.models.resource import LabourTeam
                l_res = await db.execute(select(LabourTeam).where(LabourTeam.id == assign_in.resource_id))
                l = l_res.scalar_one_or_none()
                if l: resource_name = f"Labour Team ({l.skills})"
                
            date_str = work_date.strftime("%b %d")
            msg = f"{resource_name} assigned to {farm_name} for {date_str}"
            
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
                message=msg
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
    assign.status = AssignmentStatus.COMPLETED
    
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
        
        # Fetch dynamic resource name
        resource_name = assign.resource_type.capitalize()
        if assign.resource_type == 'machine':
            from app.models.resource import Machine
            m_res = await db.execute(select(Machine).where(Machine.id == assign.resource_id))
            m = m_res.scalar_one_or_none()
            if m: resource_name = m.type
        elif assign.resource_type == 'labour':
            from app.models.resource import LabourTeam
            l_res = await db.execute(select(LabourTeam).where(LabourTeam.id == assign.resource_id))
            l = l_res.scalar_one_or_none()
            if l: resource_name = f"Labour Team ({l.skills})"
            
        msg = f"{resource_name} work completed at {farm_name}"
        
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
            message=msg
        )
        
    return assign


# --- Background Worker & Reassignment Flow ---

async def run_assignment_engine_background():
    async with AsyncSessionLocal() as db:
        from app.services.assignment_engine import AssignmentEngine
        engine = AssignmentEngine()
        await engine.process_sequential_dispatch(db)

def trigger_assignment_engine(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_assignment_engine_background)

async def handle_partial_recovery_or_reassign(
    db: AsyncSession,
    request: Request,
    cancelled_assignment: Assignment,
    background_tasks: Optional[BackgroundTasks] = None
):
    from app.services.assignment_engine import AssignmentEngine
    from app.models.farm import Farm
    
    # 1. Check if request is labour and partial_allowed is true
    if request.type == RequestType.LABOUR and request.partial_allowed:
        # Calculate remaining workers from active assignments (excluding this one)
        active_assigns_query = select(Assignment).where(
            Assignment.request_id == request.id,
            Assignment.status.in_([AssignmentStatus.SCHEDULED, AssignmentStatus.COMPLETED]),
            Assignment.id != cancelled_assignment.id
        )
        res = await db.execute(active_assigns_query)
        active_assigns = res.scalars().all()
        
        remaining_workers = sum(a.workers_assigned for a in active_assigns)
        missing_workers = request.workers_required - remaining_workers
        
        if missing_workers > 0:
            engine = AssignmentEngine()
            
            # Fetch farm and farms cache
            farm_res = await db.execute(select(Farm).where(Farm.id == request.farm_id))
            farm = farm_res.scalar_one_or_none()
            if not farm:
                for a in active_assigns:
                    a.status = AssignmentStatus.CANCELLED
                request.status = RequestStatus.UNSERVICED
                await db.commit()
                return
            
            f_res = await db.execute(select(Farm))
            farms = {f.id: f for f in f_res.scalars().all()}
            
            spent_budget = sum(a.final_cost for a in active_assigns)
            remaining_budget = (request.max_total_budget - spent_budget) if request.max_total_budget else None
            
            # Create a temp request for search
            temp_req = Request(
                id=request.id,
                farmer_id=request.farmer_id,
                farm_id=request.farm_id,
                type=request.type,
                required_by_date=request.required_by_date,
                start_time=request.start_time,
                end_time=request.end_time,
                duration=request.duration,
                workers_required=missing_workers,
                partial_allowed=True,
                max_budget_per_hour=request.max_budget_per_hour,
                max_total_budget=remaining_budget,
                reassignment_attempts=request.reassignment_attempts,
                created_at=request.created_at,
                priority_score=request.priority_score
            )
            
            candidates = await engine.get_eligible_labour_teams(db, temp_req, farm, datetime.now(timezone.utc), farms)
            
            if candidates:
                scored_candidates = []
                for team, dist, cost, free_slots in candidates:
                    score = engine.calculate_candidate_score(temp_req, team, dist, cost, free_slots, datetime.now(timezone.utc))
                    schedule = await engine.get_resource_schedule(db, "labour", team.id, temp_req.required_by_date.date())
                    utilization = sum(s.duration for s in schedule)
                    scored_candidates.append((score, dist, cost, utilization, team))
                
                scored_candidates.sort(key=lambda x: (-x[0], x[1], x[2], x[3]))
                
                selected_teams = []
                accumulated_workers = 0
                for score, dist, cost, util, team in scored_candidates:
                    selected_teams.append(team)
                    accumulated_workers += team.worker_count
                    if accumulated_workers >= missing_workers:
                        break
                
                if accumulated_workers >= missing_workers:
                    duration_hours = max(1, math.ceil(temp_req.duration / 60.0))
                    remaining_needed = missing_workers
                    
                    locked_teams = []
                    lock_ok = True
                    for team in selected_teams:
                        await engine.acquire_slot_lock(db, "labour", team.id, temp_req.required_by_date.date(), temp_req.id)
                        recheck_sched = await engine.resource_schedule_with_locks(db, "labour", team.id, temp_req.required_by_date.date(), temp_req.id)
                        is_valid, _ = engine.check_utilization_and_overlap(
                            temp_req.start_time,
                            temp_req.start_time + timedelta(minutes=temp_req.duration),
                            temp_req.duration,
                            recheck_sched,
                            team.lat,
                            team.lng,
                            farm.location_lat,
                            farm.location_lng,
                            team.avg_speed,
                            farms
                        )
                        if not is_valid:
                            lock_ok = False
                            break
                        locked_teams.append(team)
                        
                    if lock_ok:
                        for team in locked_teams:
                            assigned = min(team.worker_count, remaining_needed)
                            team_cost = team.cost_per_worker_per_hour * duration_hours * assigned
                            remaining_needed -= assigned
                            
                            new_assign = Assignment(
                                request_id=request.id,
                                resource_type="labour",
                                resource_id=team.id,
                                scheduled_date=datetime.combine(request.required_by_date.date(), datetime.min.time()),
                                status=AssignmentStatus.SCHEDULED,
                                start_time=request.start_time,
                                end_time=request.end_time,
                                duration=request.duration,
                                workers_assigned=assigned,
                                final_cost=team_cost
                            )
                            db.add(new_assign)
                            await engine.confirm_slot_lock(db, "labour", team.id, request.required_by_date.date(), request.id)
                        
                        await db.commit()
                        return # Safe recovery complete!
                    else:
                        await engine.release_slot_lock(db, request.id)
            
            # If replacement fails, cancel all remaining working teams
            for a in active_assigns:
                a.status = AssignmentStatus.CANCELLED
                await db.execute(delete(AvailabilityCalendar).where(
                    AvailabilityCalendar.resource_type == "labour",
                    AvailabilityCalendar.resource_id == a.resource_id,
                    AvailabilityCalendar.date == request.required_by_date.date()
                ))
                
    # 2. Fallback to full request reassignment
    request.reassignment_attempts += 1
    if request.reassignment_attempts < 3:
        request.priority_score += 10.0
        request.status = RequestStatus.PENDING
        await db.commit()
        if background_tasks:
            trigger_assignment_engine(background_tasks)
    else:
        request.status = RequestStatus.UNSERVICED
        request.priority_reason = "Max reassignment attempts exceeded."
        await db.commit()
        await notification_manager.notify_admins(
            event_type="UNSERVICED_REQUEST",
            entity_type="req",
            entity_id=request.id,
            message=f"Request #{request.id} is now UNSERVICED after exceeding reassignment attempts."
        )

async def cancel_assignment(
    db: AsyncSession,
    assignment_id: int,
    user_id: int,
    reason: str,
    background_tasks: Optional[BackgroundTasks] = None
) -> Assignment:
    from app.core.exceptions import AgriFluxException
    
    # 1. Fetch assignment and related entities
    res = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    assignment = res.scalar_one_or_none()
    if not assignment:
        raise AgriFluxException("Assignment not found.", status_code=404)
        
    res_req = await db.execute(select(Request).where(Request.id == assignment.request_id))
    request = res_req.scalar_one()
    
    # Check authorization (only farmer of the request, resource owner/leader, or admin can cancel)
    is_farmer = request.farmer_id == user_id
    
    is_owner = False
    if assignment.resource_type == 'machine':
        m_res = await db.execute(select(Machine).where(Machine.id == assignment.resource_id))
        machine = m_res.scalar_one_or_none()
        if machine and machine.owner_id == user_id:
            is_owner = True
    elif assignment.resource_type == 'labour':
        l_res = await db.execute(select(LabourTeam).where(LabourTeam.id == assignment.resource_id))
        team = l_res.scalar_one_or_none()
        if team and team.leader_id == user_id:
            is_owner = True
            
    # Also check if admin
    user_res = await db.execute(select(User).where(User.id == user_id))
    current_user = user_res.scalar_one_or_none()
    is_admin = current_user and current_user.role == 'admin'
    
    if not (is_farmer or is_owner or is_admin):
        raise AgriFluxException("Unauthorized to cancel this assignment.", status_code=403)
        
    # 2. Cutoff validation
    now_utc = datetime.now(timezone.utc)
    # Ensure start_time is timezone aware
    start_time = assignment.start_time
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
        
    cutoff_time = start_time - timedelta(minutes=240)
    is_late_cancel = now_utc > cutoff_time
    
    # 3. Update status & penalties
    if not is_late_cancel:
        # Early cancellation — status CANCELLED, request returns to PENDING for re-matching
        assignment.status = AssignmentStatus.CANCELLED
    else:
        assignment.status = AssignmentStatus.LATE_CANCEL
        assignment.is_late_cancel = True
        assignment.cancelled_by_id = user_id
        assignment.cancelled_at = now_utc
        assignment.cancellation_reason = reason

        if is_owner:
            # Penalize resource owner for late cancellation
            if assignment.resource_type == 'machine':
                m_res = await db.execute(select(Machine).where(Machine.id == assignment.resource_id))
                res_obj = m_res.scalar_one()
            else:
                l_res = await db.execute(select(LabourTeam).where(LabourTeam.id == assignment.resource_id))
                res_obj = l_res.scalar_one()

            res_obj.cooldown_until = now_utc + timedelta(minutes=240)
            res_obj.last_infraction_date = now_utc.date()
            res_obj.daily_failure_count += 1
            res_obj.failure_count += 1
            res_obj.late_cancel_count += 1
            res_obj.penalty_count += 1
        elif is_farmer:
            # Penalize farmer — late farmer cancel terminates the request as UNSERVICED
            farmer_res = await db.execute(select(User).where(User.id == request.farmer_id))
            farmer = farmer_res.scalar_one()
            farmer.late_cancel_count += 1

    # 4. Release availability slot lock
    await db.execute(delete(AvailabilityCalendar).where(
        AvailabilityCalendar.resource_type == assignment.resource_type,
        AvailabilityCalendar.resource_id == assignment.resource_id,
        AvailabilityCalendar.date == assignment.scheduled_date.date()
    ))

    # 5. Determine post-cancellation request lifecycle
    if not is_late_cancel:
        # Early cancel: return request to PENDING so the engine can re-match
        request.status = RequestStatus.PENDING
        await db.commit()
        if background_tasks:
            trigger_assignment_engine(background_tasks)
    elif is_farmer and is_late_cancel:
        # Defect 3: Farmer late cancel → terminal UNSERVICED. No reassignment.
        request.status = RequestStatus.UNSERVICED
        request.priority_reason = "Late cancellation by farmer."
        await db.commit()
        await notification_manager.notify_admins(
            event_type="UNSERVICED_REQUEST",
            entity_type="req",
            entity_id=request.id,
            message=f"Request #{request.id} marked UNSERVICED after farmer late cancellation."
        )
    else:
        # Owner/admin late cancel → Safe Partial Recovery or full reassignment
        await db.commit()
        await handle_partial_recovery_or_reassign(db, request, assignment, background_tasks)

    return assignment

async def fail_assignment(
    db: AsyncSession,
    assignment_id: int,
    reason: str,
    background_tasks: Optional[BackgroundTasks] = None
) -> Assignment:
    from app.core.exceptions import AgriFluxException
    
    res = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    assignment = res.scalar_one_or_none()
    if not assignment:
        raise AgriFluxException("Assignment not found.", status_code=404)
        
    res_req = await db.execute(select(Request).where(Request.id == assignment.request_id))
    request = res_req.scalar_one()
    
    # 1. Update status
    assignment.status = AssignmentStatus.FAILED
    assignment.failure_logged = True
    
    # 2. Penalize resource owner
    now_utc = datetime.now(timezone.utc)
    if assignment.resource_type == 'machine':
        m_res = await db.execute(select(Machine).where(Machine.id == assignment.resource_id))
        res_obj = m_res.scalar_one()
    else:
        l_res = await db.execute(select(LabourTeam).where(LabourTeam.id == assignment.resource_id))
        res_obj = l_res.scalar_one()
        
    res_obj.cooldown_until = now_utc + timedelta(minutes=240)
    res_obj.last_infraction_date = now_utc.date()
    res_obj.daily_failure_count += 1
    res_obj.failure_count += 1
    res_obj.penalty_count += 1
    
    # 3. Release lock
    await db.execute(delete(AvailabilityCalendar).where(
        AvailabilityCalendar.resource_type == assignment.resource_type,
        AvailabilityCalendar.resource_id == assignment.resource_id,
        AvailabilityCalendar.date == assignment.scheduled_date.date()
    ))
    
    await db.commit()
    
    # 4. Trigger recovery
    await handle_partial_recovery_or_reassign(db, request, assignment, background_tasks)
    return assignment

async def no_show_assignment(
    db: AsyncSession,
    assignment_id: int,
    is_owner_no_show: bool,
    background_tasks: Optional[BackgroundTasks] = None
) -> Assignment:
    from app.core.exceptions import AgriFluxException
    
    res = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    assignment = res.scalar_one_or_none()
    if not assignment:
        raise AgriFluxException("Assignment not found.", status_code=404)
        
    res_req = await db.execute(select(Request).where(Request.id == assignment.request_id))
    request = res_req.scalar_one()
    
    # 1. Update status
    assignment.status = AssignmentStatus.NO_SHOW
    
    now_utc = datetime.now(timezone.utc)
    
    # 2. Penalize
    if is_owner_no_show:
        if assignment.resource_type == 'machine':
            m_res = await db.execute(select(Machine).where(Machine.id == assignment.resource_id))
            res_obj = m_res.scalar_one()
        else:
            l_res = await db.execute(select(LabourTeam).where(LabourTeam.id == assignment.resource_id))
            res_obj = l_res.scalar_one()
            
        res_obj.cooldown_until = now_utc + timedelta(minutes=240)
        res_obj.last_infraction_date = now_utc.date()
        res_obj.daily_no_show_count += 1
        res_obj.no_show_count += 1
        res_obj.penalty_count += 1
    else:
        # Farmer no-show
        farmer_res = await db.execute(select(User).where(User.id == request.farmer_id))
        farmer = farmer_res.scalar_one()
        farmer.no_show_count += 1
        
    # 3. Release lock
    await db.execute(delete(AvailabilityCalendar).where(
        AvailabilityCalendar.resource_type == assignment.resource_type,
        AvailabilityCalendar.resource_id == assignment.resource_id,
        AvailabilityCalendar.date == assignment.scheduled_date.date()
    ))

    await db.commit()

    # 4. Post no-show lifecycle
    if not is_owner_no_show:
        # Defect 4: Farmer no-show → terminal UNSERVICED. No reassignment.
        request.status = RequestStatus.UNSERVICED
        request.priority_reason = "Farmer no-show."
        await db.commit()
        await notification_manager.notify_admins(
            event_type="UNSERVICED_REQUEST",
            entity_type="req",
            entity_id=request.id,
            message=f"Request #{request.id} marked UNSERVICED after farmer no-show."
        )
    else:
        # Owner no-show → Safe Partial Recovery or full reassignment
        await handle_partial_recovery_or_reassign(db, request, assignment, background_tasks)

    return assignment
