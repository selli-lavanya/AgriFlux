from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.operations import Request, RequestStatus
from app.models.farm import Farm
from app.services.weather_service import weather_service

class PriorityEngine:
    async def evaluate_pending_requests(self, db: AsyncSession):
        """
        Core Scheduling Logic: Scans all pending requests and dynamically shifts
        their priority_score based on localized weather threats and crop urgency.
        """
        result = await db.execute(select(Request).where(Request.status == RequestStatus.PENDING))
        requests = result.scalars().all()
        
        for req in requests:
            # 1. Fetch related Farm
            farm_res = await db.execute(select(Farm).where(Farm.id == req.farm_id))
            farm = farm_res.scalar_one_or_none()
            
            if not farm:
                continue
                
            # Baseline priority
            score = 10.0
            
            # 2. Check localized weather risk for these exact coordinates
            weather_data = await weather_service.get_forecast(farm.location_lat, farm.location_lng)
            
            if weather_data.get("risk_level") == "HIGH":
                score += 50.0  # Massive score spike to cut the line
                req.priority_reason = weather_data.get("condition")
                
            # 3. Assess Crop Stage Bottlenecks
            if farm.crop_stage == "Harvest-Ready":
                score += 30.0  # Crops dying in the field get extreme priority
                
            req.priority_score = score
            
        await db.commit()
        return {"processed_count": len(requests), "algorithm_applied": "Weather-Crop-Matrix"}

priority_engine = PriorityEngine()
