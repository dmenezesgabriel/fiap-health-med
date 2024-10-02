import logging
import os

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

    for table in tables:
        try:
            table.wait_until_exists()
            logger.info(f"Table {table.table_name} created successfully.")
        except ClientError as e:
            logger.error(
                f"Error creating table: {e.response['Error']['Message']}"
            )


if __name__ == "__main__":
    create_tables()
