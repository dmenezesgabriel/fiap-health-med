import logging
import os
from typing import Dict

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

dynamodb = boto3.resource(
    "dynamodb", endpoint_url=os.getenv("AWS_ENDPOINT_URL")
)
appointment_table = dynamodb.Table("appointments")


class DynamoDBAppointmentRepository:
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
