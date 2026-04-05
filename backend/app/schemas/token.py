from pydantic import BaseModel
from typing import Optional
from app.models.user import UserRole

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: int

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[UserRole] = None
