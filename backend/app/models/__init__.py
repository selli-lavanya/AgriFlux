from app.models.user import User
from app.models.farm import Farm
from app.models.resource import Machine, LabourTeam
from app.models.operations import Request, Assignment
from app.models.availability import AvailabilityCalendar, Alert

# This ensures all models are loaded so Alembic can detect them globally
