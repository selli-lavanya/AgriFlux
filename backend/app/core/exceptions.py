from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from app.api.responses import ErrorResponse

class AgriFluxException(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, details: str = None):
        self.message = message
        self.status_code = status_code
        self.details = details

async def agriflux_exception_handler(request: Request, exc: AgriFluxException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            message=exc.message,
            details=exc.details
        ).model_dump(exclude_none=True),
    )

async def unhandled_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                message=exc.detail,
                details=None
            ).model_dump(exclude_none=True),
        )
    
    import logging
    logging.error(f"UNHANDLED EXCEPTION: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            message="Internal System Error",
            details="The core matrix encountered an unhandled disturbance. Logs have been generated."
        ).model_dump(),
    )
