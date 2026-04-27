from fastapi import APIRouter, Depends, Query, HTTPException, status
from sse_starlette.sse import EventSourceResponse
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
import jwt
from app.core.config import settings
from app.services.notification_service import notification_manager
import asyncio

router = APIRouter()

@router.get("/stream")
async def notification_stream(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    """
    SSE endpoint for clients to listen to real-time events.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401)
        
    result = await db.execute(select(User).where(User.id == int(user_id)))
    current_user = result.scalar_one_or_none()
    if not current_user:
        raise HTTPException(status_code=401)
        
    import logging
    logging.info(f"SSE: User {current_user.id} ({current_user.role}) initiated stream connection.")
    
    async def event_generator():
        # Subscribe
        queue = await notification_manager.subscribe(current_user.id, current_user.role)
        try:
            while True:
                # Blocks until an event payload is placed into this user's queue.
                data = await queue.get()
                
                # Yield SSE chunk
                yield {
                    "event": "message",
                    "data": data
                }
        except asyncio.CancelledError:
            logging.info(f"SSE: User {current_user.id} connection cancelled.")
            pass
        finally:
            logging.info(f"SSE: User {current_user.id} unsubscribed.")
            notification_manager.unsubscribe(queue, current_user.id, current_user.role)
            
    return EventSourceResponse(event_generator())
