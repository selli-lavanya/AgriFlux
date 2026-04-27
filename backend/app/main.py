from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.responses import SuccessResponse
from app.core.exceptions import AgriFluxException, agriflux_exception_handler, unhandled_exception_handler
from app.api.endpoints import auth, farms, machines, labour, requests, assignments, alerts, copilot, notifications, analytics
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AgriFlux")

def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )

    # Add exception handlers
    application.add_exception_handler(AgriFluxException, agriflux_exception_handler)
    application.add_exception_handler(Exception, unhandled_exception_handler)

    @application.middleware("http")
    async def log_requests(request, call_next):
        # Skip logging for long-running SSE streams to avoid blocking or late logs
        if "/notifications/stream" in request.url.path:
            return await call_next(request)
            
        start_time = time.time()
        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.2f}ms")
            return response
        except Exception as e:
            logger.error(f"Middleware Error: {str(e)}")
            raise e

    # CORS outermost layer - Restored specific origins for credentials support
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Attach modules
    application.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
    application.include_router(farms.router, prefix=f"{settings.API_V1_STR}/farms", tags=["farms"])
    application.include_router(machines.router, prefix=f"{settings.API_V1_STR}/machines", tags=["machines"])
    application.include_router(labour.router, prefix=f"{settings.API_V1_STR}/labour", tags=["labour_teams"])
    application.include_router(requests.router, prefix=f"{settings.API_V1_STR}/requests", tags=["requests"])
    application.include_router(assignments.router, prefix=f"{settings.API_V1_STR}/assignments", tags=["assignments"])
    application.include_router(alerts.router, prefix=f"{settings.API_V1_STR}/alerts", tags=["alerts"])
    application.include_router(copilot.router, prefix=f"{settings.API_V1_STR}/copilot", tags=["copilot"])
    application.include_router(notifications.router, prefix=f"{settings.API_V1_STR}/notifications", tags=["notifications"])
    application.include_router(analytics.router, prefix=f"{settings.API_V1_STR}/analytics", tags=["analytics"])

    return application

app = get_application()

@app.get("/health", response_model=SuccessResponse, tags=["Health"])
def health_check():
    return SuccessResponse(message="Service is healthy", data={"version": settings.VERSION})
