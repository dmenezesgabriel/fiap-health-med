# user_service/main.py
import os
from datetime import datetime
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field

app = FastAPI()

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
        try:
            response = user_table.get_item(Key={"email": email})
            return response.get("Item")
        except ClientError as e:
            print(e.response["Error"]["Message"])
            return None

    @staticmethod
    async def create_user(user: User):
        try:
            user_table.put_item(Item=user.dict())
            return True
        except ClientError as e:
            print(e.response["Error"]["Message"])
            return False

    @staticmethod
    async def update_user(user: User):
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
            return True
        except ClientError as e:
            print(e.response["Error"]["Message"])
            return False

    @staticmethod
    async def get_all_doctors():
        try:
            response = user_table.scan(
                FilterExpression="attribute_exists(crm)"
            )
            return response.get("Items", [])
        except ClientError as e:
            print(e.response["Error"]["Message"])
            return []


class AvailabilityRepository:
    @staticmethod
    async def add_availability(availability: DailyAvailability):
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
            return True
        except ClientError as e:
            print(e.response["Error"]["Message"])
            return False

    @staticmethod
    async def get_doctor_availability(doctor_email: str):
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
            return availability
        except ClientError as e:
            print(e.response["Error"]["Message"])
            return {}

    @staticmethod
    async def update_availability(
        doctor_email: str, update: AvailabilityUpdate
    ):
        try:
            old_day_time_slot = (
                f"{update.day}#{update.old_start_time}-{update.old_end_time}"
            )

            # If new times are provided, update the item
            if update.new_start_time and update.new_end_time:
                new_day_time_slot = f"{update.day}#{update.new_start_time}-{update.new_end_time}"

                # First, add the new item
                availability_table.put_item(
                    Item={
                        "doctor_email": doctor_email,
                        "day_time_slot": new_day_time_slot,
                        "start_time": update.new_start_time,
                        "end_time": update.new_end_time,
                    }
                )

                # Then, delete the old item
                availability_table.delete_item(
                    Key={
                        "doctor_email": doctor_email,
                        "day_time_slot": old_day_time_slot,
                    }
                )
            else:
                # If no new times are provided, just update the existing item
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
            return True
        except ClientError as e:
            print(e.response["Error"]["Message"])
            return False

    @staticmethod
    async def delete_availability(
        doctor_email: str, delete: AvailabilityDelete
    ):
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
            return True
        except ClientError as e:
            print(e.response["Error"]["Message"])
            return False


class UserService:
    @staticmethod
    async def create_user(user: User):
        existing_user = await UserRepository.get_user(user.email)
        if existing_user:
            return False
        return await UserRepository.create_user(user)

    @staticmethod
    async def get_user(email: str):
        return await UserRepository.get_user(email)

    @staticmethod
    async def update_user(user: User):
        existing_user = await UserRepository.get_user(user.email)
        if not existing_user:
            return False
        return await UserRepository.update_user(user)

    @staticmethod
    async def get_all_doctors():
        return await UserRepository.get_all_doctors()

    @staticmethod
    async def add_availability(availability: DailyAvailability):
        return await AvailabilityRepository.add_availability(availability)

    @staticmethod
    async def get_doctor_availability(doctor_email: str):
        return await AvailabilityRepository.get_doctor_availability(
            doctor_email
        )

    @staticmethod
    async def update_availability(
        doctor_email: str, update: AvailabilityUpdate
    ):
        return await AvailabilityRepository.update_availability(
            doctor_email, update
        )

    @staticmethod
    async def delete_availability(
        doctor_email: str, delete: AvailabilityDelete
    ):
        return await AvailabilityRepository.delete_availability(
            doctor_email, delete
        )


@app.post("/users")
async def create_user(user: User):
    success = await UserService.create_user(user)
    if not success:
        raise HTTPException(status_code=400, detail="User already exists")
    return {"message": "User created successfully"}


@app.get("/users/{email}")
async def get_user(email: str):
    user = await UserService.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/users/{email}")
async def update_user(email: str, user: User):
    if email != user.email:
        raise HTTPException(
            status_code=400, detail="Email in path must match email in body"
        )
    success = await UserService.update_user(user)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User updated successfully"}


@app.get("/doctors")
async def get_all_doctors():
    doctors = await UserService.get_all_doctors()
    return doctors


@app.post("/doctors/{doctor_email}/availability")
async def add_doctor_availability(
    doctor_email: str, availability: DailyAvailability
):
    if doctor_email != availability.doctor_email:
        raise HTTPException(
            status_code=400,
            detail="Doctor email in path must match email in body",
        )
    success = await UserService.add_availability(availability)
    if not success:
        raise HTTPException(
            status_code=400, detail="Failed to add availability"
        )
    return {"message": "Availability added successfully"}


@app.get("/doctors/{doctor_email}/availability")
async def get_doctor_availability(doctor_email: str):
    availability = await UserService.get_doctor_availability(doctor_email)
    return availability


@app.put("/doctors/{doctor_email}/availability")
async def update_doctor_availability(
    doctor_email: str, update: AvailabilityUpdate
):
    success = await UserService.update_availability(doctor_email, update)
    if not success:
        raise HTTPException(
            status_code=400, detail="Failed to update availability"
        )
    return {"message": "Availability updated successfully"}


@app.delete("/doctors/{doctor_email}/availability")
async def delete_doctor_availability(
    doctor_email: str, delete: AvailabilityDelete
):
    success = await UserService.delete_availability(doctor_email, delete)
    if not success:
        raise HTTPException(
            status_code=400, detail="Failed to delete availability"
        )
    return {"message": "Availability deleted successfully"}
