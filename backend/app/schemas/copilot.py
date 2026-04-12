from pydantic import BaseModel
from typing import List, Optional

class ChatMessage(BaseModel):
    role: str
    content: str
    
class CopilotQuery(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []

class CopilotResponse(BaseModel):
    reply: str
