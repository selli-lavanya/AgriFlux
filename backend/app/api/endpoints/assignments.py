from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List
from datetime import datetime, timedelta
from app.db.database import get_db
from app.schemas.operations import AssignmentCreate, AssignmentOut
from app.services import operations_service
from app.api.deps import RoleChecker, get_current_user
from app.models.user import User, UserRole

router = APIRouter()

admin_only = RoleChecker([UserRole.ADMIN])
providers_only = RoleChecker([UserRole.MACHINE_OWNER, UserRole.LABOUR_TEAM])

@router.post("/", response_model=AssignmentOut)
async def dispatch_assignment(
    assignment_in: AssignmentCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(admin_only)
):
    return await operations_service.create_assignment(db, assign_in=assignment_in)

@router.get("/my-tasks", response_model=List[AssignmentOut])
async def get_my_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(providers_only)
):
    return await operations_service.get_assignments_for_provider(db, current_user.id, current_user.role)

@router.put("/{assignment_id}/complete", response_model=AssignmentOut)
async def complete_task(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(providers_only)
):
    return await operations_service.complete_assignment(db, assignment_id)

@router.put("/{assignment_id}/cancel", response_model=AssignmentOut)
async def cancel_task(
    assignment_id: int,
    reason: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await operations_service.cancel_assignment(
        db, 
        assignment_id=assignment_id, 
        user_id=current_user.id, 
        reason=reason,
        background_tasks=background_tasks
    )

@router.put("/{assignment_id}/fail", response_model=AssignmentOut)
async def fail_task(
    assignment_id: int,
    reason: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await operations_service.fail_assignment(
        db,
        assignment_id=assignment_id,
        reason=reason,
        background_tasks=background_tasks
    )

@router.put("/{assignment_id}/no-show", response_model=AssignmentOut)
async def no_show_task(
    assignment_id: int,
    is_owner_no_show: bool,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    return await operations_service.no_show_assignment(
        db,
        assignment_id=assignment_id,
        is_owner_no_show=is_owner_no_show,
        background_tasks=background_tasks
    )

@router.get("/availability")
async def get_system_availability(db: AsyncSession = Depends(get_db)):
    from app.models.resource import Machine, LabourTeam
    from app.models.operations import Assignment
    
    # Query massive total inventory metrics
    mc_res = await db.execute(select(func.count(Machine.id)))
    total_machines = mc_res.scalar() or 0
    
    lc_res = await db.execute(select(func.count(LabourTeam.id)))
    total_labour = lc_res.scalar() or 0
    
    from sqlalchemy import cast, Date
    
    # Query all active network demands
    query = select(Assignment).where(Assignment.status != 'COMPLETED')
    assigns = await db.execute(query)
    active = assigns.scalars().all()
    
    calendar = {}
    # Use UTC-aware date for baseline to avoid shifting offsets
    base_date = datetime.now().date()
    
    for i in range(7):
        target = base_date + timedelta(days=i)
        target_str = target.isoformat()
        
        # Count using exact date match
        m_booked = sum(1 for a in active if a.scheduled_date.date() == target and a.resource_type == 'machine')
        l_booked = sum(1 for a in active if a.scheduled_date.date() == target and a.resource_type == 'labour')
        
        calendar[target_str] = {
            "date": target_str,
            "machines": {
                "total": total_machines, 
                "booked": m_booked, 
                "available": max(0, total_machines - m_booked)
            },
            "labour": {
                "total": total_labour, 
                "booked": l_booked, 
                "available": max(0, total_labour - l_booked)
            }
        }
        
    return list(calendar.values())
