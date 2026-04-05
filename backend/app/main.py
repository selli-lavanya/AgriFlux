from fastapi import FastAPI

app = FastAPI(title="AgriFlux API")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "agriflux"}
