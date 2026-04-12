import asyncio
from app.db.database import AsyncSessionLocal
from app.models.operations import Request, Assignment, RequestStatus
from sqlalchemy import select
from sqlalchemy import func
from datetime import datetime, timedelta
import json

async def test_admin():
    async with AsyncSessionLocal() as db:
        try:
            # 1. PENDING REQUESTS
            result_req = await db.execute(select(Request).where(Request.status == RequestStatus.PENDING))
            pend_reqs = result_req.scalars().all()
            
            # 2. LOCAL AVAILABILITY
            from app.models.resource import Machine, LabourTeam
            mc_res = await db.execute(select(func.count(Machine.id)))
            total_machines = mc_res.scalar() or 0
            
            lc_res = await db.execute(select(func.count(LabourTeam.id)))
            total_labour = lc_res.scalar() or 0
            
            query = select(Assignment).where(Assignment.status != 'completed')
            assigns = await db.execute(query)
            active = assigns.scalars().all()
            
            availability = []
            base_date = datetime.now().date()
            for i in range(7):
                target = base_date + timedelta(days=i)
                m_booked = sum(1 for a in active if a.scheduled_date.date() == target and a.resource_type == 'machine')
                l_booked = sum(1 for a in active if a.scheduled_date.date() == target and a.resource_type == 'labour')
                availability.append({
                    "date": target.isoformat(),
                    "machines": {"total": total_machines, "booked": m_booked, "available": total_machines - m_booked},
                    "labour": {"total": total_labour, "booked": l_booked, "available": total_labour - l_booked}
                })
            
            context_data = {}
            context_data["Pending_Requests"] = [{"id": r.id, "farm_id": r.farm_id, "type": r.type, "priority_score": r.priority_score, "priority_reason": r.priority_reason} for r in pend_reqs]
            context_data["7_Day_Availability"] = availability
            
            # 3. JSON DUMPS
            context_str = json.dumps(context_data, indent=2, default=str)
            print("SUCCESS! Output length:", len(context_str))
            
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_admin())
