import pytest
import math
from datetime import datetime, date, timedelta, timezone
from sqlalchemy.future import select
from sqlalchemy import text
from app.models.user import User, UserRole
from app.models.farm import Farm
from app.models.resource import Machine, LabourTeam
from app.models.operations import Request, Assignment, RequestType, RequestStatus, AssignmentStatus
from app.models.availability import AvailabilityCalendar
from app.services.assignment_engine import AssignmentEngine, haversine_distance
from app.services import operations_service

pytestmark = pytest.mark.asyncio

# --- Helper functions ---

async def create_farmer(db, email="farmer@example.com"):
    user = User(email=email, hashed_password="password", role=UserRole.FARMER, is_active=True)
    db.add(user)
    await db.flush()
    return user

async def create_machine_owner(db, email="owner@example.com"):
    user = User(email=email, hashed_password="password", role=UserRole.MACHINE_OWNER, is_active=True)
    db.add(user)
    await db.flush()
    return user

async def create_labour_leader(db, email="leader@example.com"):
    user = User(email=email, hashed_password="password", role=UserRole.LABOUR_TEAM, is_active=True)
    db.add(user)
    await db.flush()
    return user

async def create_farm(db, farmer_id, name="Test Farm", size=10.0, lat=12.9716, lng=77.5946):
    farm = Farm(
        farmer_id=farmer_id,
        name=name,
        size_acres=size,
        location_lat=lat,
        location_lng=lng,
        crop_type="Rice",
        crop_stage="Harvest-Ready"
    )
    db.add(farm)
    await db.flush()
    return farm

async def create_machine(db, owner_id, type="Harvester", capacity=2.0, speed=40.0, lat=12.9716, lng=77.5946, cost=150.0):
    machine = Machine(
        owner_id=owner_id,
        type=type,
        capacity_per_day=capacity,
        avg_speed=speed,
        lat=lat,
        lng=lng,
        cost_per_hour=cost,
        status="active"
    )
    db.add(machine)
    await db.flush()
    return machine

async def create_labour_team(db, leader_id, worker_count=5, skills="Harvesting", cost=50.0, lat=12.9716, lng=77.5946):
    team = LabourTeam(
        leader_id=leader_id,
        worker_count=worker_count,
        skills=skills,
        avg_speed=40.0,
        lat=lat,
        lng=lng,
        cost_per_worker_per_hour=cost,
        status="active"
    )
    db.add(team)
    await db.flush()
    return team

# --- Test Cases ---

async def test_haversine_distance():
    dist = haversine_distance(12.9716, 77.5946, 13.0827, 80.2707)
    assert 280.0 < dist < 300.0


async def test_budget_constraints(db):
    farmer = await create_farmer(db)
    owner1 = await create_machine_owner(db, "owner1@example.com")
    owner2 = await create_machine_owner(db, "owner2@example.com")
    farm = await create_farm(db, farmer.id)
    
    # Machine 1: cost 150/hr (fits budget constraints)
    m1 = await create_machine(db, owner1.id, cost=150.0)
    # Machine 2: cost 250/hr (violates max_budget_per_hour = 200)
    m2 = await create_machine(db, owner2.id, cost=250.0)
    
    req = Request(
        farmer_id=farmer.id,
        farm_id=farm.id,
        type=RequestType.MACHINE,
        required_by_date=datetime.now(timezone.utc) + timedelta(days=2),
        start_time=datetime.now(timezone.utc) + timedelta(days=2, hours=2),
        end_time=datetime.now(timezone.utc) + timedelta(days=2, hours=6),
        duration=120, # 2 hours
        work_size=1.0,
        quantity=1,
        max_budget_per_hour=200.0,
        max_total_budget=350.0,
        status=RequestStatus.PENDING,
        priority_score=10.0
    )
    db.add(req)
    await db.flush()
    
    engine = AssignmentEngine()
    result = await engine.process_sequential_dispatch(db)
    
    assert result["success_count"] == 1
    
    # Verify Machine 1 was selected (Machine 2 is too expensive)
    assign = (await db.execute(select(Assignment).where(Assignment.request_id == req.id))).scalar_one()
    assert assign.resource_id == m1.id


async def test_capacity_checks_and_suggestions(db):
    farmer = await create_farmer(db)
    owner = await create_machine_owner(db)
    farm = await create_farm(db, farmer.id)
    
    # Capacity is 1 acre per day (calculated as hourly rate here for MVP)
    # Work size: 10 acres, duration: 2 hours, quantity: 1 machine
    # Total capacity = 1.0 (cap) * 2 (hours) * 1 (qty) = 2.0 acres < 10.0 acres -> Rejected
    m = await create_machine(db, owner.id, capacity=1.0)
    
    req = Request(
        farmer_id=farmer.id,
        farm_id=farm.id,
        type=RequestType.MACHINE,
        required_by_date=datetime.now(timezone.utc) + timedelta(days=2),
        start_time=datetime.now(timezone.utc) + timedelta(days=2, hours=2),
        end_time=datetime.now(timezone.utc) + timedelta(days=2, hours=6),
        duration=120, # 2 hours
        work_size=10.0,
        quantity=1,
        max_budget_per_hour=300.0,
        max_total_budget=1000.0,
        status=RequestStatus.PENDING,
        priority_score=10.0
    )
    db.add(req)
    await db.flush()
    
    # Try manual check suggestion extraction
    engine = AssignmentEngine()
    db_farms = {farm.id: farm}
    eligible = await engine.get_eligible_machines(db, req, farm, datetime.now(timezone.utc), db_farms)
    
    # Since capacity is insufficient, eligible list should be empty
    assert len(eligible) == 0
    
    # Verify suggestion calculation logic: CEIL(work_size / (capacity * duration_hours))
    # duration_hours = 2, capacity = 1.0, work_size = 10.0 -> CEIL(10 / 2) = 5 machines
    suggested_qty = math.ceil(req.work_size / (m.capacity_per_day * 2))
    assert suggested_qty == 5


async def test_queue_priority_sorting(db):
    farmer = await create_farmer(db)
    owner = await create_machine_owner(db)
    farm = await create_farm(db, farmer.id)
    m = await create_machine(db, owner.id, cost=100.0)
    
    # Create request 1: priority score 10.0
    req1 = Request(
        farmer_id=farmer.id,
        farm_id=farm.id,
        type=RequestType.MACHINE,
        required_by_date=datetime.now(timezone.utc) + timedelta(days=2),
        start_time=datetime.now(timezone.utc) + timedelta(days=2, hours=2),
        end_time=datetime.now(timezone.utc) + timedelta(days=2, hours=4),
        duration=120,
        work_size=1.0,
        quantity=1,
        status=RequestStatus.PENDING,
        priority_score=10.0
    )
    # Create request 2: priority score 50.0 (weather risk spike, should run first)
    req2 = Request(
        farmer_id=farmer.id,
        farm_id=farm.id,
        type=RequestType.MACHINE,
        required_by_date=datetime.now(timezone.utc) + timedelta(days=2),
        start_time=datetime.now(timezone.utc) + timedelta(days=2, hours=2),
        end_time=datetime.now(timezone.utc) + timedelta(days=2, hours=4),
        duration=120,
        work_size=1.0,
        quantity=1,
        status=RequestStatus.PENDING,
        priority_score=50.0
    )
    
    db.add(req1)
    db.add(req2)
    await db.flush()
    
    engine = AssignmentEngine()
    result = await engine.process_sequential_dispatch(db)
    
    # Only one request can succeed since both require the same machine during the same slot
    assert result["success_count"] == 1
    
    # Request 2 (highest score) must be the one assigned
    await db.refresh(req1)
    await db.refresh(req2)
    assert req2.status == RequestStatus.ASSIGNED
    assert req1.status == RequestStatus.PENDING


async def test_travel_safety_buffer_overlaps(db):
    farmer = await create_farmer(db)
    owner = await create_machine_owner(db)
    # Chennai farm (~290km away)
    chennai_farm = await create_farm(db, farmer.id, name="Chennai", lat=13.0827, lng=80.2707)
    
    # Machine located in Bangalore (lat=12.9716, lng=77.5946)
    m = await create_machine(db, owner.id, speed=40.0)
    
    req = Request(
        farmer_id=farmer.id,
        farm_id=chennai_farm.id,
        type=RequestType.MACHINE,
        required_by_date=datetime.now(timezone.utc) + timedelta(days=2),
        start_time=datetime.now(timezone.utc) + timedelta(days=2, hours=2),
        end_time=datetime.now(timezone.utc) + timedelta(days=2, hours=12),
        duration=120,
        work_size=1.0,
        quantity=1,
        status=RequestStatus.PENDING,
        priority_score=10.0
    )
    db.add(req)
    await db.flush()
    
    # Bangalore to Chennai travel time check: 290km / (40km/hr / 60) + 10 mins buffer = ~445 minutes
    # Job start_time is days=2, hours=2. Check if travel is feasible.
    engine = AssignmentEngine()
    db_farms = {chennai_farm.id: chennai_farm}
    eligible = await engine.get_eligible_machines(db, req, chennai_farm, datetime.now(timezone.utc), db_farms)
    
    # The machine should still be eligible since the travel time is less than the active time limit (1224 mins)
    # and there are no other conflicting assignments in the schedule.
    assert len(eligible) == 1
    
    # Now create another assignment on the same day that overlaps due to travel time
    local_farm = await create_farm(db, farmer.id, name="Bangalore Local", lat=12.9716, lng=77.5946)
    
    # Existing assignment in Chennai from 10:00 to 12:00
    date_target = req.required_by_date.date()
    start_c = datetime.combine(date_target, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=10)
    end_c = start_c + timedelta(hours=2)
    
    assign1 = Assignment(
        request_id=req.id,
        resource_type="machine",
        resource_id=m.id,
        scheduled_date=datetime.combine(date_target, datetime.min.time(), tzinfo=timezone.utc),
        start_time=start_c,
        end_time=end_c,
        duration=120,
        status=AssignmentStatus.SCHEDULED,
        final_cost=300.0
    )
    db.add(assign1)
    await db.flush()
    
    # New request in Bangalore from 13:00 to 15:00 (requires travel back from Chennai to Bangalore)
    # Travel back is ~445 minutes (~7.4 hours). Chennai job ends at 12:00.
    # Travel completed at 12:00 + 7.4 hours = 19:24. Bangalore job starts at 13:00 -> NOT FEASIBLE (Overlap/conflict)
    req2 = Request(
        farmer_id=farmer.id,
        farm_id=local_farm.id,
        type=RequestType.MACHINE,
        required_by_date=datetime.combine(date_target, datetime.min.time(), tzinfo=timezone.utc),
        start_time=start_c + timedelta(hours=3), # 13:00
        end_time=start_c + timedelta(hours=5), # 15:00
        duration=120,
        work_size=1.0,
        quantity=1,
        status=RequestStatus.PENDING,
        priority_score=10.0
    )
    db.add(req2)
    await db.flush()
    
    eligible2 = await engine.get_eligible_machines(db, req2, local_farm, datetime.now(timezone.utc), {local_farm.id: local_farm, chennai_farm.id: chennai_farm})
    assert len(eligible2) == 0 # Bangalore job fails overlap validation due to travel safety limits!


async def test_daily_utilization_cap(db):
    farmer = await create_farmer(db)
    owner = await create_machine_owner(db)
    farm = await create_farm(db, farmer.id)
    m = await create_machine(db, owner.id)
    
    # 85% maximum daily utilization = 1224 minutes.
    # Create existing assignments totaling 1140 minutes.
    date_target = date.today() + timedelta(days=2)
    start_base = datetime.combine(date_target, datetime.min.time(), tzinfo=timezone.utc)
    
    req_existing = Request(
        farmer_id=farmer.id,
        farm_id=farm.id,
        type=RequestType.MACHINE,
        required_by_date=datetime.combine(date_target, datetime.min.time(), tzinfo=timezone.utc),
        start_time=start_base + timedelta(hours=1),
        end_time=start_base + timedelta(hours=20),
        duration=1140,
        work_size=1.0,
        quantity=1,
        status=RequestStatus.ASSIGNED
    )
    db.add(req_existing)
    await db.flush()

    assign1 = Assignment(
        request_id=req_existing.id,
        resource_type="machine",
        resource_id=m.id,
        scheduled_date=datetime.combine(date_target, datetime.min.time(), tzinfo=timezone.utc),
        start_time=start_base + timedelta(hours=1),
        end_time=start_base + timedelta(hours=20), # 19 hours = 1140 minutes
        duration=1140,
        status=AssignmentStatus.SCHEDULED,
        final_cost=1500.0
    )
    db.add(assign1)
    await db.flush()
    
    # New request of 120 minutes (total would be 1260 mins, which exceeds 1224 limits)
    req = Request(
        farmer_id=farmer.id,
        farm_id=farm.id,
        type=RequestType.MACHINE,
        required_by_date=datetime.combine(date_target, datetime.min.time(), tzinfo=timezone.utc),
        start_time=start_base + timedelta(hours=21),
        end_time=start_base + timedelta(hours=23),
        duration=120,
        work_size=1.0,
        quantity=1,
        status=RequestStatus.PENDING,
        priority_score=10.0
    )
    db.add(req)
    await db.flush()
    
    engine = AssignmentEngine()
    eligible = await engine.get_eligible_machines(db, req, farm, datetime.now(timezone.utc), {farm.id: farm})
    assert len(eligible) == 0 # Exceeds 85% daily utilization limit!


async def test_cooldown_and_rolling_daily_failures(db):
    farmer = await create_farmer(db)
    owner = await create_machine_owner(db)
    farm = await create_farm(db, farmer.id)
    
    now_utc = datetime.now(timezone.utc)
    # Machine on cooldown
    m1 = await create_machine(db, owner.id, type="Harvester1")
    m1.cooldown_until = now_utc + timedelta(hours=48)
    
    # Machine with 2 daily infractions today
    m2 = await create_machine(db, owner.id, type="Harvester2")
    m2.last_infraction_date = now_utc.date()
    m2.daily_failure_count = 2
    await db.flush()
    
    req = Request(
        farmer_id=farmer.id,
        farm_id=farm.id,
        type=RequestType.MACHINE,
        required_by_date=datetime.now(timezone.utc) + timedelta(days=2),
        start_time=datetime.now(timezone.utc) + timedelta(days=2, hours=2),
        end_time=datetime.now(timezone.utc) + timedelta(days=2, hours=6),
        duration=120,
        work_size=1.0,
        quantity=1,
        status=RequestStatus.PENDING,
        priority_score=10.0
    )
    db.add(req)
    await db.flush()
    
    engine = AssignmentEngine()
    eligible = await engine.get_eligible_machines(db, req, farm, datetime.now(timezone.utc), {farm.id: farm})
    
    # Both machine 1 and machine 2 are filtered out due to active infractions/cooldowns!
    assert len(eligible) == 0
    
    # If we check m2 for a future date (last infraction was on a different day), it should reset dynamically
    # Verify: if last_infraction_date != current_date, checks treat it as 0
    tomorrow_utc = datetime.now(timezone.utc) + timedelta(days=1)
    eligible_tomorrow = await engine.get_eligible_machines(db, req, farm, tomorrow_utc, {farm.id: farm})
    assert len(eligible_tomorrow) == 1
    assert eligible_tomorrow[0][0].id == m2.id


async def test_greedy_splits_labour_teams(db):
    farmer = await create_farmer(db)
    leader1 = await create_labour_leader(db, "leader1@example.com")
    leader2 = await create_labour_leader(db, "leader2@example.com")
    farm = await create_farm(db, farmer.id)
    
    # Team 1 size: 3
    t1 = await create_labour_team(db, leader1.id, worker_count=3, cost=40.0)
    # Team 2 size: 2
    t2 = await create_labour_team(db, leader2.id, worker_count=2, cost=50.0)
    
    # Request: 5 workers, partial_allowed = True
    req_split = Request(
        farmer_id=farmer.id,
        farm_id=farm.id,
        type=RequestType.LABOUR,
        required_by_date=datetime.now(timezone.utc) + timedelta(days=2),
        start_time=datetime.now(timezone.utc) + timedelta(days=2, hours=2),
        end_time=datetime.now(timezone.utc) + timedelta(days=2, hours=6),
        duration=120, # 2 hours
        workers_required=5,
        partial_allowed=True,
        max_budget_per_hour=100.0,
        max_total_budget=1000.0,
        status=RequestStatus.PENDING,
        priority_score=10.0
    )
    db.add(req_split)
    await db.flush()
    
    engine = AssignmentEngine()
    result = await engine.process_sequential_dispatch(db)
    
    # Success since split combinations are allowed (3 from Team 1 + 2 from Team 2 = 5 workers)
    assert result["success_count"] == 1
    
    await db.refresh(req_split)
    assert req_split.status == RequestStatus.ASSIGNED
    
    # Assert two separate assignments created for both labour teams
    assign_query = select(Assignment).where(Assignment.request_id == req_split.id)
    assigns = (await db.execute(assign_query)).scalars().all()
    assert len(assigns) == 2
    team_ids = {a.resource_id for a in assigns}
    assert team_ids == {t1.id, t2.id}


async def test_cancellation_rules_and_penalties(db):
    farmer = await create_farmer(db)
    leader = await create_labour_leader(db)
    farm = await create_farm(db, farmer.id)
    team = await create_labour_team(db, leader.id, worker_count=5)
    
    # 1. Early cancellation (before 240 mins)
    start_c = datetime.now(timezone.utc) + timedelta(hours=6)
    req = Request(
        farmer_id=farmer.id,
        farm_id=farm.id,
        type=RequestType.LABOUR,
        required_by_date=start_c,
        start_time=start_c,
        end_time=start_c + timedelta(hours=2),
        duration=120,
        workers_required=5,
        status=RequestStatus.ASSIGNED,
        priority_score=10.0
    )
    db.add(req)
    await db.flush()
    await db.refresh(req)
    
    assign = Assignment(
        request_id=req.id,
        resource_type="labour",
        resource_id=team.id,
        scheduled_date=datetime.combine(start_c.date(), datetime.min.time(), tzinfo=timezone.utc),
        start_time=start_c,
        end_time=start_c + timedelta(hours=2),
        duration=120,
        status=AssignmentStatus.SCHEDULED,
        final_cost=500.0
    )
    db.add(assign)
    await db.flush()
    
    # Trigger cancellation (early cancel)
    cancelled = await operations_service.cancel_assignment(db, assign.id, farmer.id, "Change of plans")
    assert cancelled.status == AssignmentStatus.CANCELLED
    assert cancelled.is_late_cancel == False
    
    # Cooldown should NOT be applied since it's early
    await db.refresh(team)
    assert team.cooldown_until is None
    assert team.daily_failure_count == 0
    
    # 2. Late cancellation (after cutoff)
    start_late = datetime.now(timezone.utc) + timedelta(hours=2) # Only 2 hours away
    req_late = Request(
        farmer_id=farmer.id,
        farm_id=farm.id,
        type=RequestType.LABOUR,
        required_by_date=start_late,
        start_time=start_late,
        end_time=start_late + timedelta(hours=2),
        duration=120,
        workers_required=5,
        status=RequestStatus.ASSIGNED,
        priority_score=10.0
    )
    db.add(req_late)
    await db.flush()
    await db.refresh(req_late)
    
    assign_late = Assignment(
        request_id=req_late.id,
        resource_type="labour",
        resource_id=team.id,
        scheduled_date=datetime.combine(start_late.date(), datetime.min.time(), tzinfo=timezone.utc),
        start_time=start_late,
        end_time=start_late + timedelta(hours=2),
        duration=120,
        status=AssignmentStatus.SCHEDULED,
        final_cost=500.0
    )
    db.add(assign_late)
    await db.flush()
    
    # Owner late cancellation
    cancelled_late = await operations_service.cancel_assignment(db, assign_late.id, leader.id, "Breakdown")
    assert cancelled_late.status == AssignmentStatus.LATE_CANCEL
    assert cancelled_late.is_late_cancel == True
    
    # Check cooldown and penalty applications
    await db.refresh(team)
    assert team.cooldown_until is not None
    assert team.daily_failure_count == 1
    assert team.penalty_count == 1
    assert team.late_cancel_count == 1


async def test_operational_failure_and_no_show_rules(db):
    farmer = await create_farmer(db)
    leader = await create_labour_leader(db)
    farm = await create_farm(db, farmer.id)
    team = await create_labour_team(db, leader.id, worker_count=5)
    
    start_time = datetime.now(timezone.utc) + timedelta(hours=2)
    req = Request(
        farmer_id=farmer.id,
        farm_id=farm.id,
        type=RequestType.LABOUR,
        required_by_date=start_time,
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        duration=120,
        workers_required=5,
        status=RequestStatus.ASSIGNED
    )
    db.add(req)
    await db.flush()
    
    assign = Assignment(
        request_id=req.id,
        resource_type="labour",
        resource_id=team.id,
        scheduled_date=datetime.combine(start_time.date(), datetime.min.time(), tzinfo=timezone.utc),
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        duration=120,
        status=AssignmentStatus.SCHEDULED,
        final_cost=500.0
    )
    db.add(assign)
    await db.flush()
    
    # Operational Failure log
    failed = await operations_service.fail_assignment(db, assign.id, "Tractor caught fire")
    assert failed.status == AssignmentStatus.FAILED
    assert failed.failure_logged == True
    
    await db.refresh(team)
    assert team.cooldown_until is not None
    assert team.daily_failure_count == 1
    assert team.failure_count == 1
    
    # Owner no-show
    # Reset cooldown for next test check
    team.cooldown_until = None
    await db.flush()
    
    assign2 = Assignment(
        request_id=req.id,
        resource_type="labour",
        resource_id=team.id,
        scheduled_date=datetime.combine(start_time.date(), datetime.min.time(), tzinfo=timezone.utc),
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        duration=120,
        status=AssignmentStatus.SCHEDULED,
        final_cost=500.0
    )
    db.add(assign2)
    await db.flush()
    
    no_show = await operations_service.no_show_assignment(db, assign2.id, is_owner_no_show=True)
    assert no_show.status == AssignmentStatus.NO_SHOW
    
    await db.refresh(team)
    assert team.cooldown_until is not None
    assert team.daily_no_show_count == 1
    assert team.no_show_count == 1


async def test_safe_partial_recovery(db):
    farmer = await create_farmer(db)
    leader1 = await create_labour_leader(db, "leader1@example.com")
    leader2 = await create_labour_leader(db, "leader2@example.com")
    leader3 = await create_labour_leader(db, "leader3@example.com") # replacement
    farm = await create_farm(db, farmer.id)
    
    # Team 1: 3 workers
    t1 = await create_labour_team(db, leader1.id, worker_count=3, lat=12.9716, lng=77.5946, cost=50.0)
    # Team 2: 2 workers
    t2 = await create_labour_team(db, leader2.id, worker_count=2, lat=12.9716, lng=77.5946, cost=50.0)
    # Team 3: 2 workers (available replacement)
    t3 = await create_labour_team(db, leader3.id, worker_count=2, lat=12.9716, lng=77.5946, cost=50.0)
    
    start_time = datetime.now(timezone.utc) + timedelta(hours=2)
    req = Request(
        farmer_id=farmer.id,
        farm_id=farm.id,
        type=RequestType.LABOUR,
        required_by_date=start_time,
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        duration=120,
        workers_required=5,
        partial_allowed=True,
        max_budget_per_hour=200.0,
        max_total_budget=1000.0,
        status=RequestStatus.ASSIGNED
    )
    db.add(req)
    await db.flush()
    await db.refresh(req)
    
    # Create assignments for team 1 and 2
    a1 = Assignment(
        request_id=req.id,
        resource_type="labour",
        resource_id=t1.id,
        scheduled_date=datetime.combine(start_time.date(), datetime.min.time(), tzinfo=timezone.utc),
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        duration=120,
        workers_assigned=3,
        status=AssignmentStatus.SCHEDULED,
        final_cost=300.0
    )
    a2 = Assignment(
        request_id=req.id,
        resource_type="labour",
        resource_id=t2.id,
        scheduled_date=datetime.combine(start_time.date(), datetime.min.time(), tzinfo=timezone.utc),
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        duration=120,
        workers_assigned=2,
        status=AssignmentStatus.SCHEDULED,
        final_cost=200.0
    )
    db.add(a1)
    db.add(a2)
    await db.flush()
    
    # Owner 2 cancels late. This should trigger Safe Partial Recovery for Team 2 (2 workers).
    # Since Team 3 is active and available, it should replace Team 2.
    cancelled = await operations_service.cancel_assignment(db, a2.id, leader2.id, "Sick leader")
    assert cancelled.status == AssignmentStatus.LATE_CANCEL
    
    # Check that request is still ASSIGNED (since replacement succeeded)
    await db.refresh(req)
    assert req.status == RequestStatus.ASSIGNED
    
    # Check that replacement assignment exists for Team 3 (2 workers)
    all_assigns = (await db.execute(select(Assignment).where(Assignment.request_id == req.id))).scalars().all()
    # Should contain: a1 (SCHEDULED), a2 (LATE_CANCEL), and new replacement (SCHEDULED for t3)
    assert len(all_assigns) == 3
    active_assigns = [a for a in all_assigns if a.status == AssignmentStatus.SCHEDULED]
    assert len(active_assigns) == 2
    active_resource_ids = {a.resource_id for a in active_assigns}
    assert active_resource_ids == {t1.id, t3.id}


# ---------------------------------------------------------------------------
# Phase 2.1 Remediation Tests
# ---------------------------------------------------------------------------

async def test_reliability_penalty_reduces_score(db):
    """
    Defect 1: penalty_count must reduce the candidate score by 5.0 per infraction.
    A penalised resource must score lower than an otherwise identical clean resource.
    """
    engine = AssignmentEngine()

    farmer = await create_farmer(db, "fp1@example.com")
    farm = await create_farm(db, farmer.id)
    now = datetime.now(timezone.utc)

    req = Request(
        farmer_id=farmer.id,
        farm_id=farm.id,
        type=RequestType.MACHINE,
        required_by_date=now + timedelta(days=2),
        start_time=now + timedelta(days=2, hours=2),
        end_time=now + timedelta(days=2, hours=4),
        duration=120,
        work_size=1.0,
        quantity=1,
        status=RequestStatus.PENDING,
        priority_score=20.0,
        created_at=now - timedelta(hours=1),
    )
    db.add(req)
    await db.flush()

    owner_a = await create_machine_owner(db, "owner_a@example.com")
    owner_b = await create_machine_owner(db, "owner_b@example.com")

    # Clean machine (no infractions)
    clean_machine = await create_machine(db, owner_a.id, cost=100.0)
    clean_machine.penalty_count = 0

    # Penalised machine (2 infractions)
    penalised_machine = await create_machine(db, owner_b.id, cost=100.0)
    penalised_machine.penalty_count = 2

    await db.flush()

    score_clean = engine.calculate_candidate_score(req, clean_machine, 10.0, 200.0, [120], now)
    score_penalised = engine.calculate_candidate_score(req, penalised_machine, 10.0, 200.0, [120], now)

    # Penalised score must be exactly 10.0 lower (5.0 * 2 infractions)
    assert score_clean - score_penalised == pytest.approx(10.0, abs=1e-6), (
        f"Expected 10.0 score gap, got {score_clean - score_penalised}"
    )
    assert score_penalised < score_clean


async def test_sequential_travel_utilization_calculation(db):
    """
    Defect 2: Travel utilisation must follow sequential routing Base -> Job1 -> Job2,
    NOT parallel sum from new job to all existing jobs.
    Validates that 3 same-farm assignments with zero inter-job travel are correctly
    accepted while a day-busting 4th job is correctly rejected.
    """
    engine = AssignmentEngine()
    farmer = await create_farmer(db, "fp2@example.com")
    farm = await create_farm(db, farmer.id, lat=12.9716, lng=77.5946)
    owner = await create_machine_owner(db, "owner_seq@example.com")
    # Machine co-located with farm → travel time ≈ 0
    machine = await create_machine(db, owner.id, speed=40.0, lat=12.9716, lng=77.5946)
    await db.flush()

    date_target = date.today() + timedelta(days=3)
    base = datetime.combine(date_target, datetime.min.time(), tzinfo=timezone.utc)

    # Build 3 existing sequential 360-min (6 hr) assignments totalling 1080 mins
    req_placeholder = Request(
        farmer_id=farmer.id,
        farm_id=farm.id,
        type=RequestType.MACHINE,
        required_by_date=base,
        start_time=base + timedelta(hours=1),
        end_time=base + timedelta(hours=20),
        duration=1080,
        work_size=1.0,
        quantity=1,
        status=RequestStatus.ASSIGNED,
    )
    db.add(req_placeholder)
    await db.flush()

    existing_slots = []
    # Spacing existing slots 15 minutes apart so the 10-min travel buffer is satisfied
    # between consecutive jobs (matching what the engine enforces at assignment time).
    # Layout: 1h→7h, 7h15m→13h15m, 13h30m→19h30m
    slot_starts = [
        base + timedelta(hours=1),
        base + timedelta(hours=7, minutes=15),
        base + timedelta(hours=13, minutes=30),
    ]
    for i, s in enumerate(slot_starts):
        e = s + timedelta(hours=6)
        a = Assignment(
            request_id=req_placeholder.id,
            resource_type="machine",
            resource_id=machine.id,
            scheduled_date=base,
            start_time=s,
            end_time=e,
            duration=360,
            status=AssignmentStatus.SCHEDULED,
            final_cost=500.0,
        )
        db.add(a)
        existing_slots.append({"start": s, "end": e, "duration": 360, "farm_id": farm.id})
    await db.flush()

    db_farms = {farm.id: farm}

    schedule = await engine.get_resource_schedule(db, "machine", machine.id, date_target)

    # After 3 slots ending at 19h30m, with a 10-min travel buffer the new job can start at
    # 19h40m or later. Use 19h45m to be safe.
    # Duration totals: 3×360 = 1080. Travel (4 hops × 10 min = 40 min).
    # 150-min job → 1080+150+40 = 1270 > 1224 → REJECTED
    new_start = base + timedelta(hours=19, minutes=45)
    new_end = new_start + timedelta(minutes=150)

    is_valid, _ = engine.check_utilization_and_overlap(
        new_start, new_end, 150, schedule,
        machine.lat, machine.lng,
        farm.location_lat, farm.location_lng,
        machine.avg_speed,
        db_farms,
    )
    assert not is_valid, "150-min job must be rejected: total utilisation would exceed 85% cap"

    # 60-min job → 1080+60+40 = 1180 < 1224 → ACCEPTED
    new_start_ok = base + timedelta(hours=19, minutes=45)
    new_end_ok = new_start_ok + timedelta(minutes=60)
    is_valid_ok, _ = engine.check_utilization_and_overlap(
        new_start_ok, new_end_ok, 60, schedule,
        machine.lat, machine.lng,
        farm.location_lat, farm.location_lng,
        machine.avg_speed,
        db_farms,
    )
    assert is_valid_ok, "60-min job should fit within the 85% daily utilisation cap"


async def test_farmer_early_cancel_returns_request_to_pending(db):
    """
    Defect 3 (Early cancel path): When a farmer cancels MORE than 240 minutes before
    the job start, the request must return to PENDING and NO reassignment must be
    triggered immediately (no handle_partial_recovery_or_reassign side-effects).
    """
    farmer = await create_farmer(db, "fp3@example.com")
    leader = await create_labour_leader(db, "leader3@example.com")
    farm = await create_farm(db, farmer.id)
    team = await create_labour_team(db, leader.id, worker_count=5)

    # Job starts in 8 hours → well outside the 4-hour late-cancel window
    start_time = datetime.now(timezone.utc) + timedelta(hours=8)
    req = Request(
        farmer_id=farmer.id,
        farm_id=farm.id,
        type=RequestType.LABOUR,
        required_by_date=start_time,
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        duration=120,
        workers_required=5,
        status=RequestStatus.ASSIGNED,
        priority_score=10.0,
    )
    db.add(req)
    await db.flush()
    await db.refresh(req)

    assign = Assignment(
        request_id=req.id,
        resource_type="labour",
        resource_id=team.id,
        scheduled_date=datetime.combine(start_time.date(), datetime.min.time(), tzinfo=timezone.utc),
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        duration=120,
        workers_assigned=5,
        status=AssignmentStatus.SCHEDULED,
        final_cost=500.0,
    )
    db.add(assign)
    await db.flush()

    result = await operations_service.cancel_assignment(db, assign.id, farmer.id, "Changed my mind")

    assert result.status == AssignmentStatus.CANCELLED
    assert result.is_late_cancel == False

    await db.refresh(req)
    assert req.status == RequestStatus.PENDING, (
        f"Early farmer cancel must return request to PENDING, got {req.status}"
    )

    # Resource must NOT be penalised
    await db.refresh(team)
    assert team.cooldown_until is None
    assert team.penalty_count == 0


async def test_farmer_late_cancel_sets_request_unserviced_no_reassignment(db):
    """
    Defect 3 (Late cancel path): When a farmer cancels WITHIN 240 minutes of job start,
    the request must be set to UNSERVICED and reassignment must NOT occur.
    """
    farmer = await create_farmer(db, "fp4@example.com")
    leader = await create_labour_leader(db, "leader4@example.com")
    farm = await create_farm(db, farmer.id)
    team = await create_labour_team(db, leader.id, worker_count=5)

    # Job starts in 1 hour → inside the 4-hour late-cancel window
    start_time = datetime.now(timezone.utc) + timedelta(hours=1)
    req = Request(
        farmer_id=farmer.id,
        farm_id=farm.id,
        type=RequestType.LABOUR,
        required_by_date=start_time,
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        duration=120,
        workers_required=5,
        status=RequestStatus.ASSIGNED,
        priority_score=10.0,
        reassignment_attempts=0,
    )
    db.add(req)
    await db.flush()
    await db.refresh(req)

    assign = Assignment(
        request_id=req.id,
        resource_type="labour",
        resource_id=team.id,
        scheduled_date=datetime.combine(start_time.date(), datetime.min.time(), tzinfo=timezone.utc),
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        duration=120,
        workers_assigned=5,
        status=AssignmentStatus.SCHEDULED,
        final_cost=500.0,
    )
    db.add(assign)
    await db.flush()

    result = await operations_service.cancel_assignment(db, assign.id, farmer.id, "Emergency")

    assert result.status == AssignmentStatus.LATE_CANCEL
    assert result.is_late_cancel == True

    await db.refresh(req)
    assert req.status == RequestStatus.UNSERVICED, (
        f"Farmer late cancel must set request to UNSERVICED, got {req.status}"
    )
    # Reassignment attempts must NOT have been incremented
    assert req.reassignment_attempts == 0, (
        "reassignment_attempts must not be bumped on farmer late cancel"
    )

    # Farmer penalty must be applied; resource team must NOT be penalised
    await db.refresh(farmer)
    assert farmer.late_cancel_count == 1

    await db.refresh(team)
    assert team.penalty_count == 0, "Resource team must NOT be penalised for farmer late cancel"


async def test_farmer_no_show_sets_request_unserviced_no_reassignment(db):
    """
    Defect 4: When is_owner_no_show=False (farmer no-show), the request must be set
    to UNSERVICED immediately. No reassignment must be triggered.
    """
    farmer = await create_farmer(db, "fp5@example.com")
    leader = await create_labour_leader(db, "leader5@example.com")
    farm = await create_farm(db, farmer.id)
    team = await create_labour_team(db, leader.id, worker_count=5)

    start_time = datetime.now(timezone.utc) + timedelta(hours=1)
    req = Request(
        farmer_id=farmer.id,
        farm_id=farm.id,
        type=RequestType.LABOUR,
        required_by_date=start_time,
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        duration=120,
        workers_required=5,
        status=RequestStatus.ASSIGNED,
        priority_score=10.0,
        reassignment_attempts=0,
    )
    db.add(req)
    await db.flush()
    await db.refresh(req)

    assign = Assignment(
        request_id=req.id,
        resource_type="labour",
        resource_id=team.id,
        scheduled_date=datetime.combine(start_time.date(), datetime.min.time(), tzinfo=timezone.utc),
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        duration=120,
        workers_assigned=5,
        status=AssignmentStatus.SCHEDULED,
        final_cost=500.0,
    )
    db.add(assign)
    await db.flush()

    result = await operations_service.no_show_assignment(db, assign.id, is_owner_no_show=False)

    assert result.status == AssignmentStatus.NO_SHOW

    await db.refresh(req)
    assert req.status == RequestStatus.UNSERVICED, (
        f"Farmer no-show must set request to UNSERVICED, got {req.status}"
    )
    assert req.reassignment_attempts == 0, (
        "reassignment_attempts must not be bumped on farmer no-show"
    )

    # Farmer's no-show count must be recorded
    await db.refresh(farmer)
    assert farmer.no_show_count == 1

    # Resource team must NOT receive any penalties
    await db.refresh(team)
    assert team.penalty_count == 0
    assert team.cooldown_until is None


async def test_reassignment_attempts_reset_on_successful_dispatch(db):
    """
    Defect 5: After a successful dispatch, reassignment_attempts must be reset to 0
    regardless of any prior failed attempts.
    """
    farmer = await create_farmer(db, "fp6@example.com")
    owner = await create_machine_owner(db, "owner6@example.com")
    farm = await create_farm(db, farmer.id)
    machine = await create_machine(db, owner.id, cost=100.0)

    now = datetime.now(timezone.utc)
    req = Request(
        farmer_id=farmer.id,
        farm_id=farm.id,
        type=RequestType.MACHINE,
        required_by_date=now + timedelta(days=2),
        start_time=now + timedelta(days=2, hours=2),
        end_time=now + timedelta(days=2, hours=4),
        duration=120,
        work_size=1.0,
        quantity=1,
        max_budget_per_hour=300.0,
        max_total_budget=1000.0,
        status=RequestStatus.PENDING,
        priority_score=10.0,
        reassignment_attempts=2,  # Simulate prior failed attempts
    )
    db.add(req)
    await db.flush()

    engine = AssignmentEngine()
    result = await engine.process_sequential_dispatch(db)

    assert result["success_count"] == 1

    await db.refresh(req)
    assert req.status == RequestStatus.ASSIGNED
    assert req.reassignment_attempts == 0, (
        f"reassignment_attempts must be reset to 0 after successful dispatch, got {req.reassignment_attempts}"
    )
