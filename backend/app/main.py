from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.responses import SuccessResponse
from app.core.exceptions import AgriFluxException, agriflux_exception_handler
from app.api.endpoints import auth, farms, machines, labour, requests, assignments, alerts, copilot

def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )

    # CORS Blocks Browser rejections when calling API from localhost:3000
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add exception handlers
    application.add_exception_handler(AgriFluxException, agriflux_exception_handler)

    # Attach modules
    application.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
    application.include_router(farms.router, prefix=f"{settings.API_V1_STR}/farms", tags=["farms"])
    application.include_router(machines.router, prefix=f"{settings.API_V1_STR}/machines", tags=["machines"])
    application.include_router(labour.router, prefix=f"{settings.API_V1_STR}/labour", tags=["labour_teams"])
    application.include_router(requests.router, prefix=f"{settings.API_V1_STR}/requests", tags=["requests"])
    application.include_router(assignments.router, prefix=f"{settings.API_V1_STR}/assignments", tags=["assignments"])
    application.include_router(alerts.router, prefix=f"{settings.API_V1_STR}/alerts", tags=["alerts"])
    application.include_router(copilot.router, prefix=f"{settings.API_V1_STR}/copilot", tags=["copilot"])

    return application

app = get_application()

@app.get("/health", response_model=SuccessResponse, tags=["Health"])
def health_check():
    return SuccessResponse(message="Service is healthy", data={"version": settings.VERSION})
