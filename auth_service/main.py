# auth_service/main.py
import os
from datetime import datetime, timedelta

import boto3
import jwt
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

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
        try:
            response = table.get_item(Key={"email": email})
            return response.get("Item")
        except ClientError as e:
            print(e.response["Error"]["Message"])
            return None

    @staticmethod
    async def create_user(user: User):
        try:
            table.put_item(Item=user.dict())
            return True
        except ClientError as e:
            print(e.response["Error"]["Message"])
            return False


# Serviço
class AuthService:
    @staticmethod
    async def authenticate(email: str, password: str):
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
            return token
        return None

    @staticmethod
    async def register(user: User):
        existing_user = await AuthRepository.get_user(user.email)
        if existing_user:
            return False
        return await AuthRepository.create_user(user)


# Rotas
@app.post("/register")
async def register(user: User):
    success = await AuthService.register(user)
    if not success:
        raise HTTPException(status_code=400, detail="User already exists")
    return {"message": "User registered successfully"}


@app.post("/login")
async def login(user: User):
    token = await AuthService.authenticate(user.email, user.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": token}
