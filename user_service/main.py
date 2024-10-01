# user_service/main.py
import logging
import os
from datetime import datetime
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(root_path="/user_service")

dynamodb = boto3.resource(
    "dynamodb", endpoint_url=os.getenv("AWS_ENDPOINT_URL")
)
user_table = dynamodb.Table("users")
availability_table = dynamodb.Table("availability")


class User(BaseModel):
    email: EmailStr
    name: str
    cpf: str
    crm: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "name": "John Doe",
                    "cpf": "123.456.789-00",
                    "crm": "CRM/SP 123456",
                }
            ]
        }
    }


class TimeSlot(BaseModel):
    start_time: datetime
    end_time: datetime

    model_config = {"json_encoders": {datetime: lambda v: v.strftime("%H:%M")}}


class DailyAvailability(BaseModel):
    doctor_email: EmailStr
    day: str
    time_slots: List[TimeSlot]

    model_config = {
        "allow_population_by_field_name": True,
        "json_schema_extra": {
            "examples": [
                {
                    "doctor_email": "doctor@example.com",
                    "day": "Monday",
                    "time_slots": [
                        {"start_time": "09:00", "end_time": "12:00"},
                        {"start_time": "14:00", "end_time": "18:00"},
                    ],
                }
            ]
        },
    }


class AvailabilityUpdate(BaseModel):
    day: str
    old_start_time: str
    old_end_time: str
    new_start_time: Optional[str] = None
    new_end_time: Optional[str] = None

    model_config = {"extra": "forbid"}


class AvailabilityDelete(BaseModel):
    day: str
    start_time: str
    end_time: str

    model_config = {"validate_assignment": True}


class UserRepository:
    @staticmethod
    async def get_user(email: str):
        logger.info(f"Attempting to retrieve user: {email}")
        try:
            response = user_table.get_item(Key={"email": email})
            if "Item" in response:
                logger.info(f"User retrieved successfully: {email}")
                return response["Item"]
            logger.info(f"User not found: {email}")
            return None
        except ClientError as e:
            logger.error(
                f"Error retrieving user: {e.response['Error']['Message']}"
            )
            return None

    @staticmethod
    async def create_user(user: User):
        logger.info(f"Attempting to create user: {user.email}")
        try:
            user_table.put_item(Item=user.dict())
            logger.info(f"User created successfully: {user.email}")
            return True
        except ClientError as e:
            logger.error(
                f"Error creating user: {e.response['Error']['Message']}"
            )
            return False

    @staticmethod
    async def update_user(user: User):
        logger.info(f"Attempting to update user: {user.email}")
        try:
            user_table.update_item(
                Key={"email": user.email},
                UpdateExpression="set #name=:n, cpf=:c, crm=:m",
                ExpressionAttributeNames={"#name": "name"},
                ExpressionAttributeValues={
                    ":n": user.name,
                    ":c": user.cpf,
                    ":m": user.crm,
                },
            )
            logger.info(f"User updated successfully: {user.email}")
            return True
        except ClientError as e:
            logger.error(
                f"Error updating user: {e.response['Error']['Message']}"
            )
            return False

    @staticmethod
    async def get_all_doctors():
        logger.info("Attempting to retrieve all doctors")
        try:
            response = user_table.scan(
                FilterExpression="attribute_exists(crm)"
            )
            doctors = response.get("Items", [])
            logger.info(f"Retrieved {len(doctors)} doctors")
            return doctors
        except ClientError as e:
            logger.error(
                f"Error retrieving doctors: {e.response['Error']['Message']}"
            )
            return []


class AvailabilityRepository:
    @staticmethod
    async def add_availability(availability: DailyAvailability):
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

    @staticmethod
    async def get_doctor_availability(doctor_email: str):
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

    @staticmethod
    async def update_availability(
        doctor_email: str, update: AvailabilityUpdate
    ):
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

    @staticmethod
    async def delete_availability(
        doctor_email: str, delete: AvailabilityDelete
    ):
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


class UserService:
    @staticmethod
    async def create_user(user: User):
        logger.info(f"Attempting to create user: {user.email}")
        existing_user = await UserRepository.get_user(user.email)
        if existing_user:
            logger.warning(f"User already exists: {user.email}")
            return False
        success = await UserRepository.create_user(user)
        if success:
            logger.info(f"User created successfully: {user.email}")
        else:
            logger.error(f"Failed to create user: {user.email}")
        return success

    @staticmethod
    async def get_user(email: str):
        logger.info(f"Attempting to retrieve user: {email}")
        user = await UserRepository.get_user(email)
        if user:
            logger.info(f"User retrieved successfully: {email}")
        else:
            logger.info(f"User not found: {email}")
        return user

    @staticmethod
    async def update_user(user: User):
        logger.info(f"Attempting to update user: {user.email}")
        existing_user = await UserRepository.get_user(user.email)
        if not existing_user:
            logger.warning(f"User not found for update: {user.email}")
            return False
        success = await UserRepository.update_user(user)
        if success:
            logger.info(f"User updated successfully: {user.email}")
        else:
            logger.error(f"Failed to update user: {user.email}")
        return success

    @staticmethod
    async def get_all_doctors():
        logger.info("Attempting to retrieve all doctors")
        doctors = await UserRepository.get_all_doctors()
        logger.info(f"Retrieved {len(doctors)} doctors")
        return doctors

    @staticmethod
    async def add_availability(availability: DailyAvailability):
        logger.info(
            f"Attempting to add availability for doctor: {availability.doctor_email}"
        )
        success = await AvailabilityRepository.add_availability(availability)
        if success:
            logger.info(
                f"Availability added successfully for doctor: {availability.doctor_email}"
            )
        else:
            logger.error(
                f"Failed to add availability for doctor: {availability.doctor_email}"
            )
        return success

    @staticmethod
    async def get_doctor_availability(doctor_email: str):
        logger.info(
            f"Attempting to retrieve availability for doctor: {doctor_email}"
        )
        availability = await AvailabilityRepository.get_doctor_availability(
            doctor_email
        )
        logger.info(f"Retrieved availability for doctor: {doctor_email}")
        return availability

    @staticmethod
    async def update_availability(
        doctor_email: str, update: AvailabilityUpdate
    ):
        logger.info(
            f"Attempting to update availability for doctor: {doctor_email}"
        )
        success = await AvailabilityRepository.update_availability(
            doctor_email, update
        )
        if success:
            logger.info(
                f"Availability updated successfully for doctor: {doctor_email}"
            )
        else:
            logger.error(
                f"Failed to update availability for doctor: {doctor_email}"
            )
        return success

    @staticmethod
    async def delete_availability(
        doctor_email: str, delete: AvailabilityDelete
    ):
        logger.info(
            f"Attempting to delete availability for doctor: {doctor_email}"
        )
        success = await AvailabilityRepository.delete_availability(
            doctor_email, delete
        )
        if success:
            logger.info(
                f"Availability deleted successfully for doctor: {doctor_email}"
            )
        else:
            logger.error(
                f"Failed to delete availability for doctor: {doctor_email}"
            )
        return success


# ... [Keep all the route definitions as they are, but add logging] ...


@app.post("/users")
async def create_user(user: User):
    logger.info(f"Received request to create user: {user.email}")
    success = await UserService.create_user(user)
    if not success:
        logger.warning(
            f"Failed to create user: {user.email}. User already exists."
        )
        raise HTTPException(status_code=400, detail="User already exists")
    logger.info(f"User created successfully: {user.email}")
    return {"message": "User created successfully"}


@app.get("/users/{email}")
async def get_user(email: str):
    logger.info(f"Received request to get user: {email}")
    user = await UserService.get_user(email)
    if not user:
        logger.warning(f"User not found: {email}")
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User retrieved successfully: {email}")
    return user


@app.put("/users/{email}")
async def update_user(email: str, user: User):
    logger.info(f"Received request to update user: {email}")
    if email != user.email:
        logger.warning(
            f"Email mismatch in update request: path={email}, body={user.email}"
        )
        raise HTTPException(
            status_code=400, detail="Email in path must match email in body"
        )
    success = await UserService.update_user(user)
    if not success:
        logger.warning(f"Failed to update user: {email}. User not found.")
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User updated successfully: {email}")
    return {"message": "User updated successfully"}


@app.get("/doctors")
async def get_all_doctors():
    logger.info("Received request to get all doctors")
    doctors = await UserService.get_all_doctors()
    logger.info(f"Retrieved {len(doctors)} doctors")
    return doctors


@app.post("/doctors/{doctor_email}/availability")
async def add_doctor_availability(
    doctor_email: str, availability: DailyAvailability
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
    success = await UserService.add_availability(availability)
    if not success:
        logger.error(f"Failed to add availability for doctor: {doctor_email}")
        raise HTTPException(
            status_code=400, detail="Failed to add availability"
        )
    logger.info(f"Availability added successfully for doctor: {doctor_email}")
    return {"message": "Availability added successfully"}


@app.get("/doctors/{doctor_email}/availability")
async def get_doctor_availability(doctor_email: str):
    logger.info(
        f"Received request to get availability for doctor: {doctor_email}"
    )
    availability = await UserService.get_doctor_availability(doctor_email)
    logger.info(f"Retrieved availability for doctor: {doctor_email}")
    return availability


@app.put("/doctors/{doctor_email}/availability")
async def update_doctor_availability(
    doctor_email: str, update: AvailabilityUpdate
):
    logger.info(
        f"Received request to update availability for doctor: {doctor_email}"
    )
    success = await UserService.update_availability(doctor_email, update)
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
    doctor_email: str, delete: AvailabilityDelete
):
    logger.info(
        f"Received request to delete availability for doctor: {doctor_email}"
    )
    success = await UserService.delete_availability(doctor_email, delete)
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
