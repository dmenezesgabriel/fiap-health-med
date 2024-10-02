# migrations/main.py
import logging
import os
import time

import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_tables():
    dynamodb = boto3.resource(
        "dynamodb", endpoint_url=os.getenv("AWS_ENDPOINT_URL")
    )

    tables = []

    # Create Auth table (combined users table)
    tables.append(
        dynamodb.create_table(
            TableName="auth",
            KeySchema=[{"AttributeName": "email", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "email", "AttributeType": "S"},
                {"AttributeName": "user_type", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "UserTypeIndex",
                    "KeySchema": [
                        {"AttributeName": "user_type", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5,
                    },
                }
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5,
            },
        )
    )

    # Create Appointments table
    tables.append(
        dynamodb.create_table(
            TableName="appointments",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"},
                {"AttributeName": "doctor_email", "AttributeType": "S"},
                {"AttributeName": "date_time", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "DoctorDateTimeIndex",
                    "KeySchema": [
                        {"AttributeName": "doctor_email", "KeyType": "HASH"},
                        {"AttributeName": "date_time", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5,
                    },
                }
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5,
            },
        )
    )

    # Create Availability table
    tables.append(
        dynamodb.create_table(
            TableName="availability",
            KeySchema=[
                {"AttributeName": "doctor_email", "KeyType": "HASH"},
                {"AttributeName": "day_time_slot", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "doctor_email", "AttributeType": "S"},
                {"AttributeName": "day_time_slot", "AttributeType": "S"},
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5,
            },
        )
    )

    # Wait for tables to be created
    for table in tables:
        try:
            table.meta.client.get_waiter("table_exists").wait(
                TableName=table.name
            )
            logger.info(f"Table created successfully: {table.name}")
        except ClientError as e:
            logger.error(f"Error creating table {table.name}: {e}")


def delete_tables():
    dynamodb = boto3.resource(
        "dynamodb", endpoint_url=os.getenv("AWS_ENDPOINT_URL")
    )

    table_names = ["auth", "appointments", "availability"]

    for table_name in table_names:
        try:
            table = dynamodb.Table(table_name)
            table.delete()
            logger.info(f"Table deleted successfully: {table_name}")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.info(f"Table does not exist: {table_name}")
            else:
                logger.error(f"Error deleting table {table_name}: {e}")


if __name__ == "__main__":
    logger.info("Starting migration process...")

    # Uncomment the next line if you want to delete existing tables before creating new ones
    # delete_tables()

    create_tables()
    logger.info("Migration process completed")
