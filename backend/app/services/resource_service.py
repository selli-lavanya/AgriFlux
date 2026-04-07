from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.resource import Machine, LabourTeam
from app.schemas.resource import MachineCreate, LabourTeamCreate

async def create_machine(db: AsyncSession, machine_in: MachineCreate, owner_id: int) -> Machine:
    db_obj = Machine(**machine_in.model_dump(), owner_id=owner_id)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_machines_by_owner(db: AsyncSession, owner_id: int):
    query = select(Machine).where(Machine.owner_id == owner_id)
    result = await db.execute(query)
    return result.scalars().all()

async def get_all_machines(db: AsyncSession):
    query = select(Machine)
    result = await db.execute(query)
    return result.scalars().all()

async def create_labour_team(db: AsyncSession, team_in: LabourTeamCreate, leader_id: int) -> LabourTeam:
    db_obj = LabourTeam(**team_in.model_dump(), leader_id=leader_id)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_labour_teams_by_leader(db: AsyncSession, leader_id: int):
    query = select(LabourTeam).where(LabourTeam.leader_id == leader_id)
    result = await db.execute(query)
    return result.scalars().all()

async def get_all_labour_teams(db: AsyncSession):
    query = select(LabourTeam)
    result = await db.execute(query)
    return result.scalars().all()
