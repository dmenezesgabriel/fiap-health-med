import logging

from fastapi import APIRouter, Depends, HTTPException
from src.common.dto import (
    AvailabilityDelete,
    AvailabilityUpdate,
    DailyAvailability,
)
from src.domain.services.availability_service import AvailabilityService
from src.infrastructure.database.dynamodb_availability_repository import (
    AvailabilityRepository,
)
from src.ports.availability_repository import AvailabilityRepositoryPort

logger = logging.getLogger(__name__)

router = APIRouter()


def get_availability_repository():
    return AvailabilityRepository()


def get_availability_service(
    repository: AvailabilityRepositoryPort = Depends(
        get_availability_repository
    ),
):
    return AvailabilityService(repository)


@router.post("/doctors/{doctor_email}/availability")
async def add_doctor_availability(
    doctor_email: str,
    availability: DailyAvailability,
    service: AvailabilityService = Depends(get_availability_service),
):
    logger.info(
        f"Received request to add availability for doctor: {doctor_email}"
    )
    if doctor_email != availability.doctor_email:
        logger.warning(
            f"Email mismatch in add availability request: path={doctor_email}, body={availability.doctor_email}"
        )
        raise HTTPException(
            status_code=400,
            detail="Doctor email in path must match email in body",
        )
    success = await service.add_availability(availability)
    if not success:
        logger.error(f"Failed to add availability for doctor: {doctor_email}")
        raise HTTPException(
            status_code=400, detail="Failed to add availability"
        )
    logger.info(f"Availability added successfully for doctor: {doctor_email}")
    return {"message": "Availability added successfully"}


@router.get("/doctors/{doctor_email}/availability")
async def get_doctor_availability(
    doctor_email: str,
    service: AvailabilityService = Depends(get_availability_service),
):
    logger.info(
        f"Received request to get availability for doctor: {doctor_email}"
    )
    availability = await service.get_doctor_availability(doctor_email)
    logger.info(f"Retrieved availability for doctor: {doctor_email}")
    return availability


@router.put("/doctors/{doctor_email}/availability")
async def update_doctor_availability(
    doctor_email: str,
    update: AvailabilityUpdate,
    service: AvailabilityService = Depends(get_availability_service),
):
    logger.info(
        f"Received request to update availability for doctor: {doctor_email}"
    )
    success = await service.update_availability(doctor_email, update)
    if not success:
        logger.error(
            f"Failed to update availability for doctor: {doctor_email}"
        )
        raise HTTPException(
            status_code=400, detail="Failed to update availability"
        )
    logger.info(
        f"Availability updated successfully for doctor: {doctor_email}"
    )
    return {"message": "Availability updated successfully"}


@router.delete("/doctors/{doctor_email}/availability")
async def delete_doctor_availability(
    doctor_email: str,
    delete: AvailabilityDelete,
    service: AvailabilityService = Depends(get_availability_service),
):
    logger.info(
        f"Received request to delete availability for doctor: {doctor_email}"
    )
    success = await service.delete_availability(doctor_email, delete)
    if not success:
        logger.error(
            f"Failed to delete availability for doctor: {doctor_email}"
        )
        raise HTTPException(
            status_code=400, detail="Failed to delete availability"
        )
    logger.info(
        f"Availability deleted successfully for doctor: {doctor_email}"
    )
    return {"message": "Availability deleted successfully"}
