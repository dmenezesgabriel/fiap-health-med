# migrations/main.py
import os
import time

import boto3


def create_tables():
    dynamodb = boto3.resource(
        "dynamodb", endpoint_url=os.getenv("AWS_ENDPOINT_URL")
    )

    # Create Auth table
    auth_table = dynamodb.create_table(
        TableName="auth",
        KeySchema=[{"AttributeName": "email", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "email", "AttributeType": "S"}
        ],
        ProvisionedThroughput={
            "ReadCapacityUnits": 5,
            "WriteCapacityUnits": 5,
        },
    )

    # Create Users table
    users_table = dynamodb.create_table(
        TableName="users",
        KeySchema=[{"AttributeName": "email", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "email", "AttributeType": "S"}
        ],
        ProvisionedThroughput={
            "ReadCapacityUnits": 5,
            "WriteCapacityUnits": 5,
        },
    )

    # Create Appointments table
    appointments_table = dynamodb.create_table(
        TableName="appointments",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "doctor_email", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "doctor_email-index",
                "KeySchema": [
                    {"AttributeName": "doctor_email", "KeyType": "HASH"}
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

    availability_table = dynamodb.create_table(
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

    print("Tables created successfully:")
    print(f"- {auth_table.table_name}")
    print(f"- {users_table.table_name}")
    print(f"- {appointments_table.table_name}")
    print(f"- {availability_table.table_name}")


if __name__ == "__main__":
    create_tables()
