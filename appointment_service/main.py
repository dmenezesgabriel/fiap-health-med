# appointment_service/main.py
import logging
import os
from datetime import datetime, time
from typing import List

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(root_path="/appointment_service")

dynamodb = boto3.resource(
    "dynamodb", endpoint_url=os.getenv("AWS_ENDPOINT_URL")
)
appointment_table = dynamodb.Table("appointments")
availability_table = dynamodb.Table("availability")


class Appointment(BaseModel):
    id: str
    doctor_email: str
    patient_email: str
    date_time: str


class AppointmentRepository:
    @staticmethod
    async def create_appointment(appointment: Appointment):
        try:
            appointment_table.put_item(
                Item=appointment.dict(),
                ConditionExpression="attribute_not_exists(id)",
            )
            logger.info(f"Appointment created successfully: {appointment.id}")
            return True
        except ClientError as e:
            if (
                e.response["Error"]["Code"]
                == "ConditionalCheckFailedException"
            ):
                logger.warning(f"Appointment already exists: {appointment.id}")
                return False
            logger.error(
                f"Error creating appointment: {e.response['Error']['Message']}"
            )
            return False

    @staticmethod
    async def get_appointment(id: str):
        try:
            response = appointment_table.get_item(Key={"id": id})
            if "Item" in response:
                logger.info(f"Appointment retrieved: {id}")
                return response["Item"]
            logger.info(f"Appointment not found: {id}")
            return None
        except ClientError as e:
            logger.error(
                f"Error retrieving appointment: {e.response['Error']['Message']}"
            )
            return None

    @staticmethod
    async def get_doctor_appointments(doctor_email: str):
        try:
            response = appointment_table.query(
                IndexName="doctor_email-index",
                KeyConditionExpression="doctor_email = :de",
                ExpressionAttributeValues={":de": doctor_email},
            )
            appointments = response.get("Items", [])
            logger.info(
                f"Retrieved {len(appointments)} appointments for doctor: {doctor_email}"
            )
            return appointments
        except ClientError as e:
            logger.error(
                f"Error retrieving doctor appointments: {e.response['Error']['Message']}"
            )
            return []


class AppointmentService:
    @staticmethod
    async def create_appointment(appointment: Appointment):
        logger.info(f"Attempting to create appointment: {appointment.id}")

        availability = await AppointmentService.get_doctor_availability(
            appointment.doctor_email
        )
        appointment_date = appointment.date_time.split("T")[0]
        appointment_time = datetime.fromisoformat(appointment.date_time).time()

        if appointment_date not in availability:
            logger.warning(
                f"Selected date {appointment_date} is not available for doctor: {appointment.doctor_email}"
            )
            return False, "Selected date is not available"

        is_available = any(
            time.fromisoformat(slot["start_time"])
            <= appointment_time
            < time.fromisoformat(slot["end_time"])
            for slot in availability[appointment_date]
        )
        if not is_available:
            logger.warning(
                f"Selected time {appointment_time} is not within doctor's availability: {appointment.doctor_email}"
            )
            return False, "Selected time is not within doctor's availability"

        existing_appointments = (
            await AppointmentRepository.get_doctor_appointments(
                appointment.doctor_email
            )
        )
        is_conflicting = any(
            appt["date_time"] == appointment.date_time
            for appt in existing_appointments
        )
        if is_conflicting:
            logger.warning(
                f"Appointment time conflicts with an existing appointment: {appointment.date_time}"
            )
            return (
                False,
                "Appointment time conflicts with an existing appointment",
            )

        success = await AppointmentRepository.create_appointment(appointment)
        if not success:
            logger.error(f"Failed to create appointment: {appointment.id}")
            return False, "Failed to create appointment"
        logger.info(f"Appointment created successfully: {appointment.id}")
        return True, "Appointment created successfully"

    @staticmethod
    async def get_doctor_appointments(doctor_email: str):
        logger.info(f"Retrieving appointments for doctor: {doctor_email}")
        return await AppointmentRepository.get_doctor_appointments(
            doctor_email
        )

    @staticmethod
    async def get_doctor_availability(doctor_email: str):
        logger.info(f"Retrieving availability for doctor: {doctor_email}")
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
                f"Error retrieving doctor availability: {e.response['Error']['Message']}"
            )
            return {}


@app.post("/appointments")
async def create_appointment(appointment: Appointment):
    logger.info(f"Received request to create appointment: {appointment.id}")
    success, message = await AppointmentService.create_appointment(appointment)
    if not success:
        logger.warning(
            f"Failed to create appointment: {appointment.id}. Reason: {message}"
        )
        raise HTTPException(status_code=400, detail=message)
    logger.info(f"Successfully created appointment: {appointment.id}")
    return {"message": message}


@app.get("/appointments/doctor/{doctor_email}")
async def get_doctor_appointments(doctor_email: str):
    logger.info(
        f"Received request to get appointments for doctor: {doctor_email}"
    )
    appointments = await AppointmentService.get_doctor_appointments(
        doctor_email
    )
    logger.info(
        f"Retrieved {len(appointments)} appointments for doctor: {doctor_email}"
    )
    return appointments


@app.get("/appointments/doctor/{doctor_email}/availability")
async def get_doctor_availability(doctor_email: str):
    logger.info(
        f"Received request to get availability for doctor: {doctor_email}"
    )
    availability = await AppointmentService.get_doctor_availability(
        doctor_email
    )
    logger.info(f"Retrieved availability for doctor: {doctor_email}")
    return availability
