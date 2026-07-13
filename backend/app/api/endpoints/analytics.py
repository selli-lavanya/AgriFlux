from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.farm import Farm
from app.models.operations import Request, Assignment, RequestStatus
from app.models.resource import Machine, LabourTeam
from app.api.responses import SuccessResponse

router = APIRouter()

@router.get("/overview", response_model=SuccessResponse)
async def get_analytics_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Cortex clearance insufficient for global analytics.")

    # 1. Farm Metrics
    farm_count = await db.scalar(select(func.count(Farm.id)))

    # 2. Request Metrics
    pending_reqs = await db.scalar(select(func.count(Request.id)).where(Request.status == RequestStatus.PENDING))
    assigned_reqs = await db.scalar(select(func.count(Request.id)).where(Request.status == RequestStatus.ASSIGNED))
    completed_reqs = await db.scalar(select(func.count(Request.id)).where(Request.status == RequestStatus.COMPLETED))

    # 3. Resource Counts
    total_machines = await db.scalar(select(func.count(Machine.id))) or 1 # Prevent div by zero
    total_labour = await db.scalar(select(func.count(LabourTeam.id))) or 1

    # 4. Utilization (Active assignments vs total resources)
    active_machine_assignments = await db.scalar(
        select(func.count(Assignment.id)).where(Assignment.resource_type == 'machine', Assignment.status != 'COMPLETED')
    )
    active_labour_assignments = await db.scalar(
        select(func.count(Assignment.id)).where(Assignment.resource_type == 'labour', Assignment.status != 'COMPLETED')
    )

    machine_utilization = (active_machine_assignments / total_machines) * 100
    labour_utilization = (active_labour_assignments / total_labour) * 100

    data = {
        "farms": {
            "total": farm_count
        },
        "requests": {
            "pending": pending_reqs,
            "assigned": assigned_reqs,
            "completed": completed_reqs,
            "total": pending_reqs + assigned_reqs + completed_reqs
        },
        "utilization": {
            "machine_pct": round(machine_utilization, 1),
            "labour_pct": round(labour_utilization, 1)
        },
        "resources": {
            "machines": total_machines,
            "labour_teams": total_labour
        }
    }

    return SuccessResponse(message="Analytics synthesized successfully", data=data)
