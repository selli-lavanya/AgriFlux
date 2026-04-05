from typing import Any, Dict, Optional
from pydantic import BaseModel

class SuccessResponse(BaseModel):
    status: str = "success"
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    details: Optional[Any] = None
