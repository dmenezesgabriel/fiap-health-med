import logging
import os
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError
from src.common.dto import DoctorResponse, UserInDB
from src.domain.exceptions import UserAlreadyExistsException
from src.ports.auth_repository import AuthRepositoryPort

logger = logging.getLogger(__name__)


class DynamoDBAuthRepository(AuthRepositoryPort):
    def __init__(self):
        self.dynamodb = boto3.resource(
            "dynamodb", endpoint_url=os.environ.get("AWS_ENDPOINT_URL")
        )
        self.table = self.dynamodb.Table("auth")

    async def get_user(self, email: str) -> Optional[UserInDB]:
        logger.info(f"Attempting to retrieve user: {email}")
        try:
            response = self.table.get_item(Key={"email": email})
            if "Item" in response:
                logger.info(f"User retrieved successfully: {email}")
                return UserInDB(**response["Item"])
            logger.info(f"User not found: {email}")
            return None
        except ClientError as e:
            logger.error(
                f"Error retrieving user: {e.response['Error']['Message']}"
            )
            return None

    async def create_user(self, user: UserInDB) -> bool:
        logger.info(f"Attempting to create user: {user.email}")
        try:
            self.table.put_item(
                Item=user.dict(),
                ConditionExpression="attribute_not_exists(email)",
            )
            logger.info(f"User created successfully: {user.email}")
            return True
        except ClientError as e:
            if (
                e.response["Error"]["Code"]
                == "ConditionalCheckFailedException"
            ):
                logger.warning(f"User already exists: {user.email}")
                raise UserAlreadyExistsException
            logger.error(
                f"Error creating user: {e.response['Error']['Message']}"
            )
            return False

    async def delete_user(self, email: str) -> bool:
        logger.info(f"Attempting to delete user: {email}")
        try:
            self.table.delete_item(Key={"email": email})
            logger.info(f"User deleted successfully: {email}")
            return True
        except ClientError as e:
            logger.error(
                f"Error deleting user: {e.response['Error']['Message']}"
            )
            return False

    async def get_all_doctors(self) -> List[DoctorResponse]:
        logger.info("Attempting to retrieve all doctors")
        try:
            response = self.table.scan(
                FilterExpression="user_type = :ut",
                ExpressionAttributeValues={":ut": "doctor"},
            )
            doctors = [
                DoctorResponse(
                    **{k: v for k, v in item.items() if k != "hashed_password"}
                )
                for item in response.get("Items", [])
            ]
            logger.info(f"Retrieved {len(doctors)} doctors")
            return doctors
        except ClientError as e:
            logger.error(
                f"Error retrieving doctors: {e.response['Error']['Message']}"
            )
            return []
