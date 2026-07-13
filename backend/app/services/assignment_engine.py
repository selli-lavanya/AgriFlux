import math
import logging
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, cast, Date, delete
from app.models.operations import Request, Assignment, RequestStatus, AssignmentStatus, RequestType
from app.models.resource import Machine, LabourTeam
from app.models.availability import AvailabilityCalendar
from app.models.farm import Farm
from app.models.user import User
from app.core.exceptions import AgriFluxException

logger = logging.getLogger("AgriFlux.AssignmentEngine")

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class AssignmentEngine:
    def __init__(self, cooldown_minutes: int = 240, travel_safety_buffer: int = 10, max_utilization_percent: float = 85.0):
        self.cooldown_minutes = cooldown_minutes
        self.travel_safety_buffer = travel_safety_buffer
        self.max_utilization_limit = max_utilization_percent / 100.0 # e.g. 0.85
        self.max_daily_minutes = 1440

    async def get_resource_schedule(self, db: AsyncSession, resource_type: str, resource_id: int, target_date: date) -> List[Assignment]:
        """Fetch all active assignments for a resource on a specific date, sorted by start_time."""
        query = select(Assignment).where(
            Assignment.resource_type == resource_type,
            Assignment.resource_id == resource_id,
            cast(Assignment.scheduled_date, Date) == target_date,
            Assignment.status.in_([AssignmentStatus.SCHEDULED, AssignmentStatus.COMPLETED])
        ).order_by(Assignment.start_time.asc())
        res = await db.execute(query)
        return res.scalars().all()

    def check_utilization_and_overlap(
        self,
        new_start: datetime,
        new_end: datetime,
        duration: int,
        schedule: List[Assignment],
        resource_lat: float,
        resource_lng: float,
        farm_lat: float,
        farm_lng: float,
        avg_speed: float,
        db_farms: Dict[int, Farm]
    ) -> Tuple[bool, List[int]]:
        """
        Verify that:
        1. The new job does not overlap with any existing assignments.
        2. Travel times between consecutive jobs are feasible.
        3. Total minutes (duration + travel times) do not exceed the 85% utilization cap.
        Returns a tuple of (is_valid, list_of_free_slots_in_minutes).
        """
        # Calculate daily active utilization minutes limit (85%)
        allowed_minutes = int(self.max_daily_minutes * self.max_utilization_limit) # 1224 mins

        # Merge new slot with existing slots and sort chronologically
        all_slots = []
        for s in schedule:
            farm_id = None
            try:
                if s.request:
                    farm_id = s.request.farm_id
            except Exception:
                pass
            all_slots.append({
                "start": s.start_time,
                "end": s.end_time,
                "duration": s.duration,
                "farm_id": farm_id
            })
        
        all_slots.append({
            "start": new_start,
            "end": new_end,
            "duration": duration,
            "farm_id": -1 # Identifier for new farm coordinates
        })
        
        all_slots.sort(key=lambda x: x["start"])

        total_duration = 0
        total_travel = 0
        prev_end = None
        prev_farm_coords = (resource_lat, resource_lng) # Start at resource base
        rest_buffer = 0

        for slot in all_slots:
            # Check overlap with previous slot
            if prev_end and slot["start"] < prev_end:
                return False, []

            # Get farm coordinates for the current slot
            if slot["farm_id"] == -1:
                curr_lat, curr_lng = farm_lat, farm_lng
            else:
                exist_farm = None
                if slot["farm_id"]:
                    exist_farm = db_farms.get(slot["farm_id"])
                
                if exist_farm:
                    curr_lat, curr_lng = exist_farm.location_lat, exist_farm.location_lng
                else:
                    curr_lat, curr_lng = resource_lat, resource_lng

            # Travel from previous location
            dist = haversine_distance(prev_farm_coords[0], prev_farm_coords[1], curr_lat, curr_lng)
            travel_time = (dist / (avg_speed / 60.0)) + self.travel_safety_buffer if avg_speed > 0 else 0
            total_travel += travel_time

            # Check feasibility of travel between consecutive slots
            if prev_end and prev_end + timedelta(minutes=int(travel_time + rest_buffer)) > slot["start"]:
                return False, []

            total_duration += slot["duration"]
            prev_end = slot["end"]
            prev_farm_coords = (curr_lat, curr_lng)

        # Exclude return-to-base travel from the final job back to Base per Option A routing rules

        # Check total daily limit constraints
        if (total_duration + total_travel) > allowed_minutes:
            return False, []

        # Calculate remaining continuous free blocks (for fragmentation score)
        day_start = datetime.combine(new_start.date(), datetime.min.time()).replace(tzinfo=new_start.tzinfo)
        day_end = datetime.combine(new_start.date(), datetime.max.time()).replace(tzinfo=new_start.tzinfo)

        free_slots = []
        curr = day_start
        for slot in all_slots:
            if slot["start"] > curr:
                diff = int((slot["start"] - curr).total_seconds() / 60.0)
                if diff >= 60: # Ignore fragments smaller than 1 hour (Issue 9 Case 2)
                    free_slots.append(diff)
            curr = slot["end"]
        if day_end > curr:
            diff = int((day_end - curr).total_seconds() / 60.0)
            if diff >= 60:
                free_slots.append(diff)

        return True, free_slots

    def calculate_candidate_score(
        self,
        request: Request,
        resource: Any,
        distance_km: float,
        final_cost: float,
        free_slots_after: List[int],
        current_time: datetime
    ) -> float:
        """
        Compute matching score for candidate:
        Score = 3.0 * request.priority_score + 1.0 * fairness_score - 0.2 * distance_km - 0.1 * final_cost - reliability_penalty + continuity_bonus - fragmentation_penalty
        """
        priority_weight = 3.0
        fairness_weight = 1.0

        # 1. Fairness Score: log(1 + wait_time_hours)
        wait_time_hours = (current_time - request.created_at).total_seconds() / 3600.0
        fairness_score = math.log1p(max(0.0, wait_time_hours))

        # 2. Distance Penalty
        distance_penalty = 0.2 * distance_km

        # 3. Cost Penalty
        cost_penalty = 0.1 * final_cost

        # 4. Fragmentation & Continuity (Issue 9)
        # largest continuous block (continuity bonus)
        largest_block = max(free_slots_after) if free_slots_after else 0
        continuity_bonus = largest_block / 60.0 # convert to hours for scale balance
        
        # fragment count penalty
        fragment_penalty = len(free_slots_after)

        # 5. Overloaded resource utilization penalty (load balancing)
        overloading_penalty = 0.0

        # 6. Reliability Penalty (Defect 1)
        reliability_penalty = 5.0 * float(resource.penalty_count or 0)
        
        score = (
            (priority_weight * request.priority_score) +
            (fairness_weight * fairness_score) -
            distance_penalty -
            cost_penalty -
            overloading_penalty -
            reliability_penalty -
            fragment_penalty +
            continuity_bonus
        )
        return score

    async def get_eligible_machines(
        self,
        db: AsyncSession,
        request: Request,
        farm: Farm,
        current_time: datetime,
        db_farms: Dict[int, Farm]
    ) -> List[Tuple[Machine, float, float, List[int]]]:
        """Find and filter all eligible Machines, returning their distance and free slots details."""
        # Retrieve all machines
        res = await db.execute(select(Machine))
        machines = res.scalars().all()
        eligible = []

        duration_hours = max(1, math.ceil(request.duration / 60.0))
        target_date = request.required_by_date.date()

        for machine in machines:
            # Hard Filters:
            # 1. Status & Cooldown Checks
            if machine.status != "active":
                continue
            if machine.cooldown_until and machine.cooldown_until > current_time:
                continue
            # 2. Daily infraction limit checking
            if machine.last_infraction_date == current_time.date() and machine.daily_failure_count >= 2:
                continue
            # 3. Coordinates present check
            if machine.lat is None or machine.lng is None:
                continue

            # 4. Capacity validation: capacity * duration * quantity >= work_size
            # (treating capacity_per_day as hourly work size coverage rate to match Issue 3 guidelines)
            total_capacity = machine.capacity_per_day * duration_hours * request.quantity
            if request.work_size and total_capacity < request.work_size:
                continue

            # 5. Budget constraints validation: hourly cost and total cost bounds
            if request.max_budget_per_hour and machine.cost_per_hour > request.max_budget_per_hour:
                continue
            final_cost = machine.cost_per_hour * duration_hours * request.quantity
            if request.max_total_budget and final_cost > request.max_total_budget:
                continue

            # 6. Schedule fits check
            job_end = request.start_time + timedelta(minutes=request.duration)
            if job_end > request.end_time:
                continue

            schedule = await self.resource_schedule_with_locks(db, "machine", machine.id, target_date, request.id)
            dist = haversine_distance(machine.lat, machine.lng, farm.location_lat, farm.location_lng)
            
            # Map machine coords as base coordinates
            is_valid, free_slots = self.check_utilization_and_overlap(
                request.start_time,
                job_end,
                request.duration,
                schedule,
                machine.lat,
                machine.lng,
                farm.location_lat,
                farm.location_lng,
                machine.avg_speed,
                db_farms
            )
            if not is_valid:
                continue

            eligible.append((machine, dist, final_cost, free_slots))

        return eligible

    async def get_eligible_labour_teams(
        self,
        db: AsyncSession,
        request: Request,
        farm: Farm,
        current_time: datetime,
        db_farms: Dict[int, Farm]
    ) -> List[Tuple[LabourTeam, float, float, List[int]]]:
        """Find and filter all eligible Labour Teams, returning distance and free slots details."""
        res = await db.execute(select(LabourTeam))
        teams = res.scalars().all()
        eligible = []

        duration_hours = max(1, math.ceil(request.duration / 60.0))
        target_date = request.required_by_date.date()

        for team in teams:
            # Hard Filters
            if team.status != "active":
                continue
            if team.cooldown_until and team.cooldown_until > current_time:
                continue
            if team.last_infraction_date == current_time.date() and team.daily_failure_count >= 2:
                continue
            if team.lat is None or team.lng is None:
                continue

            # Capacity constraint for Labour is worker count check (no work_size capacity checks for labour)
            # If partial_allowed = False, team size must be >= workers_required
            if not request.partial_allowed and team.worker_count < request.workers_required:
                continue

            # Hourly budget check
            if request.max_budget_per_hour and team.cost_per_worker_per_hour > request.max_budget_per_hour:
                continue

            # Check time constraints
            job_end = request.start_time + timedelta(minutes=request.duration)
            if job_end > request.end_time:
                continue

            schedule = await self.resource_schedule_with_locks(db, "labour", team.id, target_date, request.id)
            dist = haversine_distance(team.lat, team.lng, farm.location_lat, farm.location_lng)
            
            is_valid, free_slots = self.check_utilization_and_overlap(
                request.start_time,
                job_end,
                request.duration,
                schedule,
                team.lat,
                team.lng,
                farm.location_lat,
                farm.location_lng,
                team.avg_speed,
                db_farms
            )
            if not is_valid:
                continue

            final_cost = team.cost_per_worker_per_hour * duration_hours * min(team.worker_count, request.workers_required)
            eligible.append((team, dist, final_cost, free_slots))

        return eligible

    async def resource_schedule_with_locks(self, db: AsyncSession, resource_type: str, resource_id: int, target_date: date, request_id: int) -> List[Assignment]:
        """Get standard schedule, overlaying active lock slots if they exist in the availability calendar."""
        schedule = await self.get_resource_schedule(db, resource_type, resource_id, target_date)
        
        # Check active locks in calendar
        lock_query = select(AvailabilityCalendar).where(
            AvailabilityCalendar.resource_type == resource_type,
            AvailabilityCalendar.resource_id == resource_id,
            AvailabilityCalendar.date == target_date,
            AvailabilityCalendar.status == "TEMP_LOCKED",
            AvailabilityCalendar.temp_lock_until > datetime.now(timezone.utc),
            AvailabilityCalendar.locked_by_request_id != request_id
        )
        lock_res = await db.execute(lock_query)
        locks = lock_res.scalars().all()
        
        # Convert locks to fake assignments for overlap checkers
        for l in locks:
            fake_assign = Assignment(
                resource_type=resource_type,
                resource_id=resource_id,
                scheduled_date=datetime.combine(target_date, datetime.min.time()),
                start_time=l.temp_lock_until - timedelta(minutes=15), # Simulated lock window
                end_time=l.temp_lock_until,
                status=AssignmentStatus.SCHEDULED
            )
            schedule.append(fake_assign)
        
        schedule.sort(key=lambda x: x.start_time)
        return schedule

    async def acquire_slot_lock(self, db: AsyncSession, resource_type: str, resource_id: int, target_date: date, request_id: int):
        """Insert lock row in availability calendar."""
        # Cleanup old locks for this request if any
        await db.execute(delete(AvailabilityCalendar).where(
            AvailabilityCalendar.locked_by_request_id == request_id
        ))
        
        lock_until = datetime.now(timezone.utc) + timedelta(minutes=2)
        lock = AvailabilityCalendar(
            resource_type=resource_type,
            resource_id=resource_id,
            date=target_date,
            status="TEMP_LOCKED",
            temp_lock_until=lock_until,
            locked_by_request_id=request_id
        )
        db.add(lock)
        await db.commit()

    async def confirm_slot_lock(self, db: AsyncSession, resource_type: str, resource_id: int, target_date: date, request_id: int):
        """Convert TEMP_LOCK to BLOCKED."""
        query = select(AvailabilityCalendar).where(
            AvailabilityCalendar.resource_type == resource_type,
            AvailabilityCalendar.resource_id == resource_id,
            AvailabilityCalendar.date == target_date,
            AvailabilityCalendar.locked_by_request_id == request_id
        )
        res = await db.execute(query)
        lock = res.scalar_one_or_none()
        if lock:
            lock.status = "BLOCKED"
            await db.commit()

    async def release_slot_lock(self, db: AsyncSession, request_id: int):
        """Release slot lock from calendar."""
        await db.execute(delete(AvailabilityCalendar).where(
            AvailabilityCalendar.locked_by_request_id == request_id
        ))
        await db.commit()

    async def process_sequential_dispatch(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Execute dispatch of all pending requests sequentially.
        Sort queue by priority_score (DESC) then created_at (ASC) to satisfy Issue 10.
        """
        # Fetch all pending requests
        q_res = await db.execute(select(Request).where(
            Request.status == RequestStatus.PENDING
        ).order_by(Request.priority_score.desc(), Request.created_at.asc()))
        pending_requests = q_res.scalars().all()

        # Cache farms to avoid multiple round-trips
        f_res = await db.execute(select(Farm))
        farms = {f.id: f for f in f_res.scalars().all()}

        dispatch_log = []
        success_count = 0
        current_time = datetime.now(timezone.utc)

        for req in pending_requests:
            farm = farms.get(req.farm_id)
            if not farm:
                req.status = RequestStatus.UNSERVICED
                req.priority_reason = "Farm location data missing."
                await db.commit()
                continue

            try:
                # Dispatch process based on request type
                if req.type == RequestType.MACHINE:
                    success = await self.dispatch_machine_request(db, req, farm, current_time, farms)
                elif req.type == RequestType.LABOUR:
                    success = await self.dispatch_labour_request(db, req, farm, current_time, farms)
                else:
                    success = False

                if success:
                    success_count += 1
                    dispatch_log.append(f"Request #{req.id} ({req.type}) assigned successfully.")
                else:
                    # Increment attempts. If exceeded, mark UNSERVICED (Issue 20 / Issue 16)
                    req.reassignment_attempts += 1
                    if req.reassignment_attempts >= 3:
                        req.status = RequestStatus.UNSERVICED
                        req.priority_reason = "No eligible resources found after max attempts."
                    else:
                        req.priority_score += 10.0 # Reassignment priority bump (Issue 7 / 12)
                    await db.commit()
                    dispatch_log.append(f"Request #{req.id} ({req.type}) failed match. Attempts: {req.reassignment_attempts}")

            except Exception as e:
                logger.error(f"Error during dispatch of request #{req.id}: {str(e)}", exc_info=True)
                await self.release_slot_lock(db, req.id)
                dispatch_log.append(f"Request #{req.id} failed due to internal error.")

        return {"processed_count": len(pending_requests), "success_count": success_count, "log": dispatch_log}

    async def dispatch_machine_request(self, db: AsyncSession, req: Request, farm: Farm, current_time: datetime, db_farms: Dict[int, Farm]) -> bool:
        """Find, score, lock, and commit best machine candidate."""
        candidates = await self.get_eligible_machines(db, req, farm, current_time, db_farms)
        if not candidates:
            return False

        # Score candidates
        scored_candidates = []
        for machine, dist, cost, free_slots in candidates:
            score = self.calculate_candidate_score(req, machine, dist, cost, free_slots, current_time)
            # Tie breaker attributes (lower distance, lower cost, lower utilization)
            schedule = await self.get_resource_schedule(db, "machine", machine.id, req.required_by_date.date())
            utilization = sum(s.duration for s in schedule)
            scored_candidates.append((score, dist, cost, utilization, machine))

        # Sort: Score DESC, Tie-breaker criteria ASC (Issue 19 tie-breaker rule)
        scored_candidates.sort(key=lambda x: (-x[0], x[1], x[2], x[3]))
        best_candidate = scored_candidates[0][4]
        best_cost = scored_candidates[0][2]
        best_dist = scored_candidates[0][1]

        # Concurrency safety: Acquire Lock, Recheck, Block (Issue 11)
        await self.acquire_slot_lock(db, "machine", best_candidate.id, req.required_by_date.date(), req.id)
        
        # Recheck
        recheck_sched = await self.resource_schedule_with_locks(db, "machine", best_candidate.id, req.required_by_date.date(), req.id)
        job_end = req.start_time + timedelta(minutes=req.duration)
        is_valid, _ = self.check_utilization_and_overlap(
            req.start_time,
            job_end,
            req.duration,
            recheck_sched,
            best_candidate.lat,
            best_candidate.lng,
            farm.location_lat,
            farm.location_lng,
            best_candidate.avg_speed,
            db_farms
        )
        if not is_valid:
            await self.release_slot_lock(db, req.id)
            return False

        # Create Assignment
        assignment = Assignment(
            request_id=req.id,
            resource_type="machine",
            resource_id=best_candidate.id,
            scheduled_date=datetime.combine(req.required_by_date.date(), datetime.min.time()),
            status=AssignmentStatus.SCHEDULED,
            start_time=req.start_time,
            end_time=req.end_time,
            duration=req.duration,
            workers_assigned=req.quantity,
            final_cost=best_cost
        )
        db.add(assignment)
        req.status = RequestStatus.ASSIGNED
        req.estimated_cost = best_cost
        req.reassignment_attempts = 0
        
        await self.confirm_slot_lock(db, "machine", best_candidate.id, req.required_by_date.date(), req.id)
        await db.commit()
        return True

    async def dispatch_labour_request(self, db: AsyncSession, req: Request, farm: Farm, current_time: datetime, db_farms: Dict[int, Farm]) -> bool:
        """Find, score, lock, and commit best labour team(s), supporting split teams if allowed."""
        candidates = await self.get_eligible_labour_teams(db, req, farm, current_time, db_farms)
        if not candidates:
            return False

        # Score candidates
        scored_candidates = []
        for team, dist, cost, free_slots in candidates:
            score = self.calculate_candidate_score(req, team, dist, cost, free_slots, current_time)
            schedule = await self.get_resource_schedule(db, "labour", team.id, req.required_by_date.date())
            utilization = sum(s.duration for s in schedule)
            scored_candidates.append((score, dist, cost, utilization, team))

        # Sort: Score DESC
        scored_candidates.sort(key=lambda x: (-x[0], x[1], x[2], x[3]))

        selected_teams = []
        accumulated_workers = 0

        # Greedy combination for split teams (Issue 7)
        if req.partial_allowed:
            for score, dist, cost, util, team in scored_candidates:
                selected_teams.append(team)
                accumulated_workers += team.worker_count
                if accumulated_workers >= req.workers_required:
                    break
            if accumulated_workers < req.workers_required:
                return False # Cannot satisfy capacity request
        else:
            # Single team must satisfy
            single_candidates = [c for c in scored_candidates if c[4].worker_count >= req.workers_required]
            if not single_candidates:
                return False
            selected_teams = [single_candidates[0][4]]

        duration_hours = max(1, math.ceil(req.duration / 60.0))
        total_cost = 0

        # Lock resources atomically
        for team in selected_teams:
            await self.acquire_slot_lock(db, "labour", team.id, req.required_by_date.date(), req.id)
            # Recheck schedule overlap
            recheck_sched = await self.resource_schedule_with_locks(db, "labour", team.id, req.required_by_date.date(), req.id)
            job_end = req.start_time + timedelta(minutes=req.duration)
            is_valid, _ = self.check_utilization_and_overlap(
                req.start_time,
                job_end,
                req.duration,
                recheck_sched,
                team.lat,
                team.lng,
                farm.location_lat,
                farm.location_lng,
                team.avg_speed,
                db_farms
            )
            if not is_valid:
                # Release lock on all locked slots
                await self.release_slot_lock(db, req.id)
                return False

        # Create assignments and compute blended costs
        remaining_needed = req.workers_required
        for team in selected_teams:
            assigned = min(team.worker_count, remaining_needed)
            team_cost = team.cost_per_worker_per_hour * duration_hours * assigned
            total_cost += team_cost
            remaining_needed -= assigned

            assignment = Assignment(
                request_id=req.id,
                resource_type="labour",
                resource_id=team.id,
                scheduled_date=datetime.combine(req.required_by_date.date(), datetime.min.time()),
                status=AssignmentStatus.SCHEDULED,
                start_time=req.start_time,
                end_time=req.end_time,
                duration=req.duration,
                workers_assigned=assigned,
                final_cost=team_cost
            )
            db.add(assignment)
            await self.confirm_slot_lock(db, "labour", team.id, req.required_by_date.date(), req.id)

        # Budget bounds validation on aggregated blended cost (Issue 8)
        if req.max_total_budget and total_cost > req.max_total_budget:
            await self.release_slot_lock(db, req.id)
            # Rollback database transaction changes manually
            await db.rollback()
            return False

        req.status = RequestStatus.ASSIGNED
        req.estimated_cost = total_cost
        req.reassignment_attempts = 0
        await db.commit()
        return True
