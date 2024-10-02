import logging
import os
from datetime import datetime
from typing import Dict, List, Tuple

import boto3
import requests
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

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
                IndexName="DoctorDateTimeIndex",
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

        availability, error_msg = AppointmentService.check_availability(
            appointment.doctor_email, appointment.date_time
        )

        if not availability:
            return False, error_msg

        existing_appointments = (
            await AppointmentRepository.get_doctor_appointments(
                appointment.doctor_email
            )
        )

        appointment_date = appointment.date_time.split("T")[0]
        appointment_time = datetime.fromisoformat(appointment.date_time).time()

        is_conflicting = any(
            appt["date_time"].split("T")[0] == appointment_date
            and abs(
                (
                    datetime.fromisoformat(appt["date_time"])
                    - datetime.fromisoformat(appointment.date_time)
                ).total_seconds()
            )
            < 3600  # less than 1 hour difference
            for appt in existing_appointments
        )

        if is_conflicting:
            logger.warning(
                f"Appointment time conflicts with an existing appointment within 1 hour: {appointment.date_time}"
            )
            return (
                False,
                "Appointment time conflicts with an existing appointment within 1 hour",
            )

        success = await AppointmentRepository.create_appointment(appointment)
        if not success:
            logger.error(f"Failed to create appointment: {appointment.id}")
            return False, "Failed to create appointment"
        logger.info(f"Appointment created successfully: {appointment.id}")
        return True, "Appointment created successfully"

    @staticmethod
    def check_availability(
        doctor_email: str, date_time: str
    ) -> Tuple[bool, str]:
        logger.info(
            f"Checking availability for doctor {doctor_email} at {date_time}"
        )
        try:
            response = requests.get(
                f"{os.getenv('AVAILABILITY_SERVICE_URL')}/doctors/{doctor_email}/availability"
            )
            if response.status_code != 200:
                logger.error(
                    f"Failed to fetch availability from service. Status code: {response.status_code}"
                )
                return False, "Failed to check availability"

            availability = response.json()
            appointment_date = date_time.split("T")[0]
            appointment_time = datetime.fromisoformat(date_time).time()

            date_part = appointment_date[0:10]
            if date_part not in availability:
                logger.warning(
                    f"Selected date {appointment_date} is not available for doctor: {doctor_email}"
                )
                logger.info(f"Available dates: {list(availability.keys())}")
                return False, "Selected date is not available"

            is_available = any(
                datetime.strptime(slot["start_time"], "%H:%M").time()
                <= appointment_time
                < datetime.strptime(slot["end_time"], "%H:%M").time()
                for slot in availability[date_part]
            )

            if not is_available:
                logger.warning(
                    f"Selected time {appointment_time} is not available for doctor: {doctor_email}"
                )
                logger.info(
                    f"Available slots for {appointment_date}: {availability[date_part]}"
                )
                return False, "Selected time is not available"

            logger.info(
                f"Appointment time {appointment_time} is available for doctor: {doctor_email}"
            )
            return True, "Time is available"
        except requests.RequestException as e:
            logger.exception(f"Error while checking availability: {e}")
            return False, "Error while checking availability"
        except Exception as e:
            logger.exception(
                f"Unexpected error while checking availability: {e}"
            )
            return False, "Unexpected error while checking availability"

    @staticmethod
    async def get_doctor_appointments(
        doctor_email: str,
    ) -> Dict[str, List[Dict[str, str]]]:
        logger.info(f"Retrieving appointments for doctor: {doctor_email}")
        appointments = await AppointmentRepository.get_doctor_appointments(
            doctor_email
        )

        formatted_appointments = {}
        for appt in appointments:
            appointment_date = appt["date_time"].split("T")[0]
            appointment_time = appt["date_time"].split("T")[1][:5]
            if appointment_date not in formatted_appointments:
                formatted_appointments[appointment_date] = []
            formatted_appointments[appointment_date].append(
                {"start_time": appointment_time}
            )

        return formatted_appointments


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
    logger.info(f"Retrieved appointments for doctor: {doctor_email}")
    return appointments
