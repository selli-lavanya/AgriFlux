from fastapi import FastAPI
from app.core.config import settings
from app.api.responses import SuccessResponse
from app.core.exceptions import AgriFluxException, agriflux_exception_handler

def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )

    # Add exception handlers
    application.add_exception_handler(AgriFluxException, agriflux_exception_handler)

    # TODO: Include API routers here in future phases
    # application.include_router(api_router, prefix=settings.API_V1_STR)

    return application

app = get_application()

@app.get("/health", response_model=SuccessResponse, tags=["Health"])
def health_check():
    return SuccessResponse(message="Service is healthy", data={"version": settings.VERSION})
