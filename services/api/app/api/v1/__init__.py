from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    appointments,
    auth,
    clinician,
    discovery,
    me,
    messaging,
    prescriptions,
    records,
    video,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(me.router, prefix="/me", tags=["Patient Profile"])
api_router.include_router(discovery.router, tags=["Discovery"])
api_router.include_router(appointments.router, tags=["Appointments"])
api_router.include_router(video.router, tags=["Video"])
api_router.include_router(messaging.router, tags=["Messaging"])
api_router.include_router(records.router, tags=["Records & Documents"])
api_router.include_router(prescriptions.router, tags=["Prescriptions"])
api_router.include_router(clinician.router, prefix="/clinician", tags=["Clinician Portal"])
api_router.include_router(admin.router, prefix="/admin", tags=["Administration"])
