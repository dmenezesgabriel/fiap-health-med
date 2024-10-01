# auth_service/main.py
import logging
import os
from datetime import datetime, timedelta

import boto3
import jwt
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(root_path="/auth_service")

# Configuração do DynamoDB
dynamodb = boto3.resource(
    "dynamodb", endpoint_url=os.environ.get("AWS_ENDPOINT_URL")
)
table = dynamodb.Table("auth")


# Entidade
class User(BaseModel):
    email: str
    password: str


# Repositório
class AuthRepository:
    @staticmethod
    async def get_user(email: str):
        logger.info(f"Attempting to retrieve user: {email}")
        try:
            response = table.get_item(Key={"email": email})
            if "Item" in response:
                logger.info(f"User retrieved successfully: {email}")
                return response["Item"]
            logger.info(f"User not found: {email}")
            return None
        except ClientError as e:
            logger.error(
                f"Error retrieving user: {e.response['Error']['Message']}"
            )
            return None

    @staticmethod
    async def create_user(user: User):
        logger.info(f"Attempting to create user: {user.email}")
        try:
            table.put_item(Item=user.dict())
            logger.info(f"User created successfully: {user.email}")
            return True
        except ClientError as e:
            logger.error(
                f"Error creating user: {e.response['Error']['Message']}"
            )
            return False


# Serviço
class AuthService:
    @staticmethod
    async def authenticate(email: str, password: str):
        logger.info(f"Attempting to authenticate user: {email}")
        user = await AuthRepository.get_user(email)
        if user and user["password"] == password:
            token = jwt.encode(
                {
                    "email": email,
                    "exp": datetime.utcnow() + timedelta(hours=1),
                },
                "secret",
                algorithm="HS256",
            )
            logger.info(f"User authenticated successfully: {email}")
            return token
        logger.warning(f"Authentication failed for user: {email}")
        return None

    @staticmethod
    async def register(user: User):
        logger.info(f"Attempting to register user: {user.email}")
        existing_user = await AuthRepository.get_user(user.email)
        if existing_user:
            logger.warning(f"User already exists: {user.email}")
            return False
        success = await AuthRepository.create_user(user)
        if success:
            logger.info(f"User registered successfully: {user.email}")
        else:
            logger.error(f"Failed to register user: {user.email}")
        return success


# Rotas
@app.post("/register")
async def register(user: User):
    logger.info(f"Received registration request for user: {user.email}")
    success = await AuthService.register(user)
    if not success:
        logger.warning(f"Registration failed for user: {user.email}")
        raise HTTPException(status_code=400, detail="User already exists")
    logger.info(f"Registration successful for user: {user.email}")
    return {"message": "User registered successfully"}


@app.post("/login")
async def login(user: User):
    logger.info(f"Received login request for user: {user.email}")
    token = await AuthService.authenticate(user.email, user.password)
    if not token:
        logger.warning(f"Login failed for user: {user.email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    logger.info(f"Login successful for user: {user.email}")
    return {"token": token}
