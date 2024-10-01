# appointment_service/main.py
import os
from datetime import datetime, time
from typing import List

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

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
            return True
        except ClientError as e:
            if (
                e.response["Error"]["Code"]
                == "ConditionalCheckFailedException"
            ):
                return False
            print(e.response["Error"]["Message"])
            return False

    @staticmethod
    async def get_appointment(id: str):
        try:
            response = appointment_table.get_item(Key={"id": id})
            return response.get("Item")
        except ClientError as e:
            print(e.response["Error"]["Message"])
            return None

    @staticmethod
    async def get_doctor_appointments(doctor_email: str):
        try:
            response = appointment_table.query(
                IndexName="doctor_email-index",
                KeyConditionExpression="doctor_email = :de",
                ExpressionAttributeValues={":de": doctor_email},
            )
            return response.get("Items", [])
        except ClientError as e:
            print(e.response["Error"]["Message"])
            return []


class AppointmentService:
    @staticmethod
    async def create_appointment(appointment: Appointment):
        # Verificar disponibilidade do médico
        availability = await AppointmentService.get_doctor_availability(
            appointment.doctor_email
        )
        appointment_date = appointment.date_time.split("T")[0]
        appointment_time = datetime.fromisoformat(appointment.date_time).time()

        if appointment_date not in availability:
            return False, "Selected date is not available"

        is_available = any(
            time.fromisoformat(slot["start_time"])
            <= appointment_time
            < time.fromisoformat(slot["end_time"])
            for slot in availability[appointment_date]
        )
        if not is_available:
            return False, "Selected time is not within doctor's availability"

        # Verificar conflitos de agendamento
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
            return (
                False,
                "Appointment time conflicts with an existing appointment",
            )

        success = await AppointmentRepository.create_appointment(appointment)
        if not success:
            return False, "Failed to create appointment"
        return True, "Appointment created successfully"

    @staticmethod
    async def get_doctor_appointments(doctor_email: str):
        return await AppointmentRepository.get_doctor_appointments(
            doctor_email
        )

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


@app.post("/appointments")
async def create_appointment(appointment: Appointment):
    success, message = await AppointmentService.create_appointment(appointment)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


@app.get("/appointments/doctor/{doctor_email}")
async def get_doctor_appointments(doctor_email: str):
    appointments = await AppointmentService.get_doctor_appointments(
        doctor_email
    )
    return appointments


@app.get("/appointments/doctor/{doctor_email}/availability")
async def get_doctor_availability(doctor_email: str):
    availability = await AppointmentService.get_doctor_availability(
        doctor_email
    )
    return availability
