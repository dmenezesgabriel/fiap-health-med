import logging

from fastapi import APIRouter, HTTPException
from src.common.dto import Appointment
from src.domain.services.appointment_service import AppointmentService

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/appointments")
async def create_appointment(appointment: Appointment):
    logger.info("Received request to create appointment")
    success, message = await AppointmentService.create_appointment(appointment)
    if not success:
        logger.warning(f"Failed to create appointment. Reason: {message}")
        raise HTTPException(status_code=400, detail=message)
    logger.info("Successfully created appointment")
    return {"message": message}


@router.get("/appointments/doctor/{doctor_email}")
async def get_doctor_appointments(doctor_email: str):
    logger.info(
        f"Received request to get appointments for doctor: {doctor_email}"
    )
    appointments = await AppointmentService.get_doctor_appointments(
        doctor_email
    )
    logger.info(f"Retrieved appointments for doctor: {doctor_email}")
    return appointments
