from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="CareConnect API",
    description="Backend API for CareConnect Telehealth Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HealthCheck(BaseModel):
    status: str

@app.get("/api/v1/health", response_model=HealthCheck, tags=["System"])
async def health_check():
    return {"status": "ok"}

# Mount API router
from app.api import router as api_router
app.include_router(api_router, tags=["API"])
