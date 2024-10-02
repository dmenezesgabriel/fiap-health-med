# auth_service/main.py
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional

import boto3
import jwt
from botocore.exceptions import ClientError
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordRequestForm,
)
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(root_path="/auth_service")

# DynamoDB configuration
dynamodb = boto3.resource(
    "dynamodb", endpoint_url=os.environ.get("AWS_ENDPOINT_URL")
)
table = dynamodb.Table("auth")

# JWT settings
SECRET_KEY = (
    "your-secret-key"  # In a real application, use a secure secret key
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security scheme for token authentication
security = HTTPBearer()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Models
class UserBase(BaseModel):
    email: EmailStr
    name: str
    cpf: str


class PatientCreate(UserBase):
    password: str


class DoctorCreate(UserBase):
    password: str
    crm: str


class PatientResponse(UserBase):
    user_type: str = "patient"


class DoctorResponse(UserBase):
    user_type: str = "doctor"
    crm: str


class UserInDB(UserBase):
    user_type: str
    hashed_password: str
    crm: Optional[str] = None


class TokenData(BaseModel):
    email: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str


# Repository
class AuthRepository:
    @staticmethod
    async def get_user(email: str):
        logger.info(f"Attempting to retrieve user: {email}")
        try:
            response = table.get_item(Key={"email": email})
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

    @staticmethod
    async def create_user(user: UserInDB):
        logger.info(f"Attempting to create user: {user.email}")
        try:
            table.put_item(
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
                return False
            logger.error(
                f"Error creating user: {e.response['Error']['Message']}"
            )
            return False

    @staticmethod
    async def delete_user(email: str):
        logger.info(f"Attempting to delete user: {email}")
        try:
            table.delete_item(Key={"email": email})
            logger.info(f"User deleted successfully: {email}")
            return True
        except ClientError as e:
            logger.error(
                f"Error deleting user: {e.response['Error']['Message']}"
            )
            return False

    @staticmethod
    async def get_all_doctors():
        logger.info("Attempting to retrieve all doctors")
        try:
            response = table.scan(
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


# Service
class AuthService:
    @staticmethod
    def verify_password(plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password):
        return pwd_context.hash(password)

    @staticmethod
    async def authenticate_user(email: str, password: str):
        user = await AuthRepository.get_user(email)
        if not user:
            return False
        if not AuthService.verify_password(password, user.hashed_password):
            return False
        return user

    @staticmethod
    def create_access_token(
        data: dict, expires_delta: Optional[timedelta] = None
    ):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_token(token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                raise HTTPException(status_code=401, detail="Invalid token")
            return TokenData(email=email)
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid token")


# Dependency
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
):
    token_data = AuthService.decode_token(credentials.credentials)
    user = await AuthRepository.get_user(email=token_data.email)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# Routes
@app.post("/register/patient", response_model=PatientResponse)
async def create_patient(user: PatientCreate):
    logger.info(f"Received request to create patient: {user.email}")
    hashed_password = AuthService.get_password_hash(user.password)
    db_user = UserInDB(
        **user.dict(), user_type="patient", hashed_password=hashed_password
    )
    success = await AuthRepository.create_user(db_user)
    if not success:
        raise HTTPException(status_code=400, detail="Email already registered")
    return PatientResponse(**user.dict())


@app.post("/register/doctor", response_model=DoctorResponse)
async def create_doctor(user: DoctorCreate):
    logger.info(f"Received request to create doctor: {user.email}")
    hashed_password = AuthService.get_password_hash(user.password)
    db_user = UserInDB(
        **user.dict(), user_type="doctor", hashed_password=hashed_password
    )
    success = await AuthRepository.create_user(db_user)
    if not success:
        raise HTTPException(status_code=400, detail="Email already registered")
    return DoctorResponse(**user.dict())


@app.delete("/users/{email}")
async def delete_user(
    email: str, current_user: UserInDB = Depends(get_current_user)
):
    logger.info(f"Received request to delete user: {email}")
    if current_user.email != email:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this user"
        )
    success = await AuthRepository.delete_user(email)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}


@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await AuthService.authenticate_user(
        form_data.username, form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = AuthService.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=PatientResponse | DoctorResponse)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    if current_user.user_type == "patient":
        return PatientResponse(**current_user.dict())
    elif current_user.user_type == "doctor":
        return DoctorResponse(**current_user.dict())
    else:
        raise HTTPException(status_code=400, detail="Invalid user type")


@app.get("/verify-token")
async def verify_token(current_user: UserInDB = Depends(get_current_user)):
    if current_user.user_type == "patient":
        user_response = PatientResponse(**current_user.dict())
    elif current_user.user_type == "doctor":
        user_response = DoctorResponse(**current_user.dict())
    else:
        raise HTTPException(status_code=400, detail="Invalid user type")
    return {"message": "Token is valid", "user": user_response}


@app.get("/doctors", response_model=List[DoctorResponse])
async def list_doctors():
    logger.info("Received request to list all doctors")
    doctors = await AuthRepository.get_all_doctors()
    return doctors
