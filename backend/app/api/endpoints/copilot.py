import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any

from app.api import deps
from app.models.user import User
from app.models.farm import Farm
from app.models.operations import Request, Assignment, RequestStatus
from app.schemas.copilot import CopilotQuery, CopilotResponse
from app.services.llm_service import llm_service
from datetime import datetime, timedelta
from sqlalchemy import func

router = APIRouter()

SYSTEM_PROMPT = """You are AgriFlux Copilot, a high-level operational intelligence assistant. You are speaking with a {role}.
Your primary mission is to optimize agricultural logistics.
Base ALL of your answers strictly on the LIVE DATABASE CONTEXT provided below.
If target data is missing or undefined in the provided context window, state that the data is unavailable.
Do NOT hallucinate operations, parameters, entities, farms, machines, requests, risks, or counts.
You are a read/query oriented assistant only. You cannot directly perform assignments, scheduling, or destructive operations."""

@router.post("/query", response_model=CopilotResponse)
async def query_copilot(
    query: CopilotQuery,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    try:
        context_data = {}
        
        if current_user.role == "farmer":
            # Get farms
            result = await db.execute(select(Farm).where(Farm.farmer_id == current_user.id))
            farms = result.scalars().all()
            # Get requests
            if farms:
                farm_ids = [f.id for f in farms]
                result_req = await db.execute(select(Request).where(Request.farm_id.in_(farm_ids)))
                reqs = result_req.scalars().all()
            else:
                reqs = []
                
            context_data["Farms"] = [{"id": f.id, "name": f.name, "label": f.location_label, "crop": f.crop_type, "risk": "See requests for risk score"} for f in farms]
            context_data["Requests"] = [{"id": r.id, "farm_id": r.farm_id, "type": r.type, "status": r.status, "priority_score": r.priority_score, "priority_reason": r.priority_reason} for r in reqs]
            
        elif current_user.role == "admin":
            # Get pending requests
            result_req = await db.execute(select(Request).where(Request.status == RequestStatus.PENDING))
            pend_reqs = result_req.scalars().all()
            
            from app.models.resource import Machine, LabourTeam
            # Get global availability
            mc_res = await db.execute(select(func.count(Machine.id)))
            total_machines = mc_res.scalar() or 0
            
            lc_res = await db.execute(select(func.count(LabourTeam.id)))
            total_labour = lc_res.scalar() or 0
            
            sq_query = select(Assignment).where(Assignment.status != 'COMPLETED')
            assigns = await db.execute(sq_query)
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
            
            context_data["Pending_Requests"] = [{"id": r.id, "farm_id": r.farm_id, "type": r.type, "priority_score": r.priority_score, "priority_reason": r.priority_reason} for r in pend_reqs]
            context_data["7_Day_Availability"] = availability
        else:
            context_data["Info"] = "No specific operational context for this role."

        context_str = json.dumps(context_data, indent=2, default=str)
        
        prompt = SYSTEM_PROMPT.format(role=current_user.role)
        
        # build history
        history_text = ""
        for msg in query.history:
            history_text += f"{msg.role.upper()}: {msg.content}\n"
            
        full_query = f"[LIVE DATABASE CONTEXT]:\n{context_str}\n\n[CHAT HISTORY]:\n{history_text}\n[NEW QUERY]: {query.message}"
        
        reply = llm_service.ask(prompt, full_query)
        
        return CopilotResponse(reply=reply)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
