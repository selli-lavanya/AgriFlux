from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List
from datetime import datetime, timedelta
from app.db.database import get_db
from app.schemas.operations import AssignmentCreate, AssignmentOut
from app.services import operations_service
from app.api.deps import RoleChecker
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

@router.get("/availability")
async def get_system_availability(db: AsyncSession = Depends(get_db)):
    from app.models.resource import Machine, LabourTeam
    from app.models.operations import Assignment
    
    # Query massive total inventory metrics
    mc_res = await db.execute(select(func.count(Machine.id)))
    total_machines = mc_res.scalar() or 0
    
    lc_res = await db.execute(select(func.count(LabourTeam.id)))
    total_labour = lc_res.scalar() or 0
    
    # Query all active network demands
    query = select(Assignment).where(Assignment.status != 'completed')
    assigns = await db.execute(query)
    active = assigns.scalars().all()
    
    calendar = {}
    base_date = datetime.now().date()
    
    for i in range(7):
        target = base_date + timedelta(days=i)
        date_str = target.isoformat()
        
        m_booked = sum(1 for a in active if a.scheduled_date.date() == target and a.resource_type == 'machine')
        l_booked = sum(1 for a in active if a.scheduled_date.date() == target and a.resource_type == 'labour')
        
        calendar[date_str] = {
            "date": date_str,
            "machines": {"total": total_machines, "booked": m_booked, "available": total_machines - m_booked},
            "labour": {"total": total_labour, "booked": l_booked, "available": total_labour - l_booked}
        }
        
    return list(calendar.values())
