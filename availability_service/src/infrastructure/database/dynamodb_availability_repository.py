import logging
import os

import boto3
from botocore.exceptions import ClientError
from src.common.dto import (
    AvailabilityDelete,
    AvailabilityUpdate,
    DailyAvailability,
)
from src.ports.availability_repository import AvailabilityRepositoryPort

logger = logging.getLogger(__name__)

dynamodb = boto3.resource(
    "dynamodb", endpoint_url=os.getenv("AWS_ENDPOINT_URL")
)
availability_table = dynamodb.Table("availability")


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
