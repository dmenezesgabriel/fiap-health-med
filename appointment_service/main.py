import logging
import os
import smtplib
import uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
SEND_EMAIL_ENABLED = os.getenv("SEND_EMAIL_ENABLED", "false").lower() == "true"


class Appointment(BaseModel):
    doctor_email: str
    patient_email: str
    date_time: str


class AppointmentRepository:
    @staticmethod
    async def create_appointment(appointment: Dict):
        try:
            appointment_table.put_item(
                Item=appointment,
                ConditionExpression="attribute_not_exists(id)",
            )
            logger.info(
                f"Appointment created successfully: {appointment['id']}"
            )
            return True
        except ClientError as e:
            if (
                e.response["Error"]["Code"]
                == "ConditionalCheckFailedException"
            ):
                logger.warning(
                    f"Appointment already exists: {appointment['id']}"
                )
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
        appointment_id = str(uuid.uuid4())
        logger.info(f"Attempting to create appointment: {appointment_id}")

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

        appointment_date = appointment.date_time.split(" ")[0]
        appointment_time = datetime.fromisoformat(appointment.date_time).time()

        is_conflicting = any(
            appt["date_time"].split(" ")[0] == appointment_date
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

        appointment_dict = appointment.dict()
        appointment_dict["id"] = appointment_id
        success = await AppointmentRepository.create_appointment(
            appointment_dict
        )
        if not success:
            logger.error(f"Failed to create appointment: {appointment_id}")
            return False, "Failed to create appointment"

        # Send email notification to the doctor
        if SEND_EMAIL_ENABLED:
            email_sent = AppointmentService.send_email_notification(
                appointment_dict
            )
            if not email_sent:
                logger.warning(
                    f"Failed to send email notification for appointment: {appointment_id}"
                )

        logger.info(f"Appointment created successfully: {appointment_id}")
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
            appointment_date = date_time.split(" ")[0]
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
            appointment_date = appt["date_time"].split(" ")[0]
            appointment_time = appt["date_time"].split(" ")[1][:5]
            if appointment_date not in formatted_appointments:
                formatted_appointments[appointment_date] = []
            formatted_appointments[appointment_date].append(
                {"start_time": appointment_time}
            )

        return formatted_appointments

    @staticmethod
    def send_email_notification(appointment: Dict) -> bool:
        logger.info(f"sending email to {appointment['doctor_email']}")
        subject = "Health&Med - Nova consulta agendada"
        body = f"""
        <html>
            <body>
                <p>Olá, Dr. {appointment['doctor_email']}!</p>
                <p>Você tem uma nova consulta marcada!</p>
                <p>Paciente: {appointment['patient_email']}</p>
                <p>Data e horário: {appointment['date_time']}</p>
            </body>
        </html>
        """

        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = appointment["doctor_email"]
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)
            logger.info(
                f"Email notification sent successfully for appointment: {appointment['id']}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            return False


@app.post("/appointments")
async def create_appointment(appointment: Appointment):
    logger.info(f"Received request to create appointment")
    success, message = await AppointmentService.create_appointment(appointment)
    if not success:
        logger.warning(f"Failed to create appointment. Reason: {message}")
        raise HTTPException(status_code=400, detail=message)
    logger.info(f"Successfully created appointment")
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
