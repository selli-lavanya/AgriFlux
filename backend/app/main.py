from fastapi import FastAPI
from app.core.config import settings
from app.api.responses import SuccessResponse
from app.core.exceptions import AgriFluxException, agriflux_exception_handler
from app.api.endpoints import auth, farms, machines, labour

def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )

    # Add exception handlers
    application.add_exception_handler(AgriFluxException, agriflux_exception_handler)

    # Attach modules
    application.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
    application.include_router(farms.router, prefix=f"{settings.API_V1_STR}/farms", tags=["farms"])
    application.include_router(machines.router, prefix=f"{settings.API_V1_STR}/machines", tags=["machines"])
    application.include_router(labour.router, prefix=f"{settings.API_V1_STR}/labour", tags=["labour_teams"])

    return application

app = get_application()

@app.get("/health", response_model=SuccessResponse, tags=["Health"])
def health_check():
    return SuccessResponse(message="Service is healthy", data={"version": settings.VERSION})
