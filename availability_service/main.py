import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(root_path="/availability_service")

dynamodb = boto3.resource(
    "dynamodb", endpoint_url=os.getenv("AWS_ENDPOINT_URL")
)
availability_table = dynamodb.Table("availability")


class TimeSlot(BaseModel):
    start_time: str
    end_time: str


class DailyAvailability(BaseModel):
    doctor_email: EmailStr
    day: str
    time_slots: List[TimeSlot]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "doctor_email": "doctor@example.com",
                    "day": "2023-05-01",
                    "time_slots": [
                        {"start_time": "09:00", "end_time": "12:00"},
                        {"start_time": "14:00", "end_time": "18:00"},
                    ],
                }
            ]
        }
    }


class AvailabilityUpdate(BaseModel):
    day: str
    old_start_time: str
    old_end_time: str
    new_start_time: Optional[str] = None
    new_end_time: Optional[str] = None


class AvailabilityDelete(BaseModel):
    day: str
    start_time: str
    end_time: str


# --- Repository Port (Abstract class for Dependency Injection) ---
class AvailabilityRepositoryPort(ABC):
    @abstractmethod
    async def add_availability(self, availability: DailyAvailability) -> bool:
        pass

    @abstractmethod
    async def get_doctor_availability(self, doctor_email: str) -> dict:
        pass

    @abstractmethod
    async def update_availability(
        self, doctor_email: str, update: AvailabilityUpdate
    ) -> bool:
        pass

    @abstractmethod
    async def delete_availability(
        self, doctor_email: str, delete: AvailabilityDelete
    ) -> bool:
        pass


# --- Concrete Implementation of Repository ---
class AvailabilityRepository(AvailabilityRepositoryPort):
    async def add_availability(self, availability: DailyAvailability) -> bool:
        logger.info(
            f"Attempting to add availability for doctor: {availability.doctor_email}"
        )
        try:
            for slot in availability.time_slots:
                day_time_slot = (
                    f"{availability.day}#{slot.start_time}-{slot.end_time}"
                )
                availability_table.put_item(
                    Item={
                        "doctor_email": availability.doctor_email,
                        "day_time_slot": day_time_slot,
                        "start_time": slot.start_time,
                        "end_time": slot.end_time,
                    }
                )
            logger.info(
                f"Availability added successfully for doctor: {availability.doctor_email}"
            )
            return True
        except ClientError as e:
            logger.error(
                f"Error adding availability: {e.response['Error']['Message']}"
            )
            return False

    async def get_doctor_availability(self, doctor_email: str) -> dict:
        logger.info(
            f"Attempting to retrieve availability for doctor: {doctor_email}"
        )
        try:
            response = availability_table.query(
                KeyConditionExpression="doctor_email = :de",
                ExpressionAttributeValues={":de": doctor_email},
            )
            availability = {}
            for item in response.get("Items", []):
                day, time_slot = item["day_time_slot"].split("#")
                if day not in availability:
                    availability[day] = []
                availability[day].append(
                    {
                        "start_time": item["start_time"],
                        "end_time": item["end_time"],
                    }
                )
            logger.info(f"Retrieved availability for doctor: {doctor_email}")
            return availability
        except ClientError as e:
            logger.error(
                f"Error retrieving availability: {e.response['Error']['Message']}"
            )
            return {}

    async def update_availability(
        self, doctor_email: str, update: AvailabilityUpdate
    ) -> bool:
        logger.info(
            f"Attempting to update availability for doctor: {doctor_email}"
        )
        try:
            old_day_time_slot = (
                f"{update.day}#{update.old_start_time}-{update.old_end_time}"
            )

            if update.new_start_time and update.new_end_time:
                new_day_time_slot = f"{update.day}#{update.new_start_time}-{update.new_end_time}"

                availability_table.put_item(
                    Item={
                        "doctor_email": doctor_email,
                        "day_time_slot": new_day_time_slot,
                        "start_time": update.new_start_time,
                        "end_time": update.new_end_time,
                    }
                )

                availability_table.delete_item(
                    Key={
                        "doctor_email": doctor_email,
                        "day_time_slot": old_day_time_slot,
                    }
                )
            else:
                availability_table.update_item(
                    Key={
                        "doctor_email": doctor_email,
                        "day_time_slot": old_day_time_slot,
                    },
                    UpdateExpression="SET start_time = :start, end_time = :end",
                    ExpressionAttributeValues={
                        ":start": update.new_start_time
                        or update.old_start_time,
                        ":end": update.new_end_time or update.old_end_time,
                    },
                )
            logger.info(
                f"Availability updated successfully for doctor: {doctor_email}"
            )
            return True
        except ClientError as e:
            logger.error(
                f"Error updating availability: {e.response['Error']['Message']}"
            )
            return False

    async def delete_availability(
        self, doctor_email: str, delete: AvailabilityDelete
    ) -> bool:
        logger.info(
            f"Attempting to delete availability for doctor: {doctor_email}"
        )
        try:
            day_time_slot = (
                f"{delete.day}#{delete.start_time}-{delete.end_time}"
            )
            availability_table.delete_item(
                Key={
                    "doctor_email": doctor_email,
                    "day_time_slot": day_time_slot,
                }
            )
            logger.info(
                f"Availability deleted successfully for doctor: {doctor_email}"
            )
            return True
        except ClientError as e:
            logger.error(
                f"Error deleting availability: {e.response['Error']['Message']}"
            )
            return False


# --- Availability Service ---
class AvailabilityService:
    def __init__(self, repository: AvailabilityRepositoryPort):
        self.repository = repository

    async def add_availability(self, availability: DailyAvailability):
        return await self.repository.add_availability(availability)

    async def get_doctor_availability(self, doctor_email: str):
        return await self.repository.get_doctor_availability(doctor_email)

    async def update_availability(
        self, doctor_email: str, update: AvailabilityUpdate
    ):
        return await self.repository.update_availability(doctor_email, update)

    async def delete_availability(
        self, doctor_email: str, delete: AvailabilityDelete
    ):
        return await self.repository.delete_availability(doctor_email, delete)


# --- Dependency Injection Setup ---
def get_availability_repository():
    return AvailabilityRepository()


def get_availability_service(
    repository: AvailabilityRepositoryPort = Depends(
        get_availability_repository
    ),
):
    return AvailabilityService(repository)


# --- API Routes ---
@app.post("/doctors/{doctor_email}/availability")
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


@app.get("/doctors/{doctor_email}/availability")
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


@app.put("/doctors/{doctor_email}/availability")
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


@app.delete("/doctors/{doctor_email}/availability")
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
