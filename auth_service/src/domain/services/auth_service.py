import logging
from datetime import datetime, timedelta
from typing import List, Optional

import jwt
from passlib.context import CryptContext
from src.common.dto import (
    DoctorCreate,
    DoctorResponse,
    PatientCreate,
    PatientResponse,
    TokenData,
    UserInDB,
)
from src.domain.exceptions import (
    InvalidCredentialsException,
    NotAuthorizedException,
    UserAlreadyExistsException,
    UserNotFoundException,
)
from src.ports.auth_repository import AuthRepositoryPort

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, repository: AuthRepositoryPort):
        self.repository = repository

    def verify_password(self, plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password):
        return pwd_context.hash(password)

    async def authenticate_user(self, email: str, password: str):
        user = await self.repository.get_user(email)
        if not user:
            raise UserNotFoundException
        if not self.verify_password(password, user.hashed_password):
            raise InvalidCredentialsException
        return user

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def decode_token(self, token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                raise InvalidCredentialsException
            return TokenData(email=email)
        except jwt.PyJWTError:
            raise InvalidCredentialsException

    async def create_patient(self, user: PatientCreate) -> PatientResponse:
        hashed_password = self.get_password_hash(user.password)
        db_user = UserInDB(
            **user.dict(), user_type="patient", hashed_password=hashed_password
        )
        success = await self.repository.create_user(db_user)
        if not success:
            raise UserAlreadyExistsException
        return PatientResponse(**user.dict())

    async def create_doctor(self, user: DoctorCreate) -> DoctorResponse:
        hashed_password = self.get_password_hash(user.password)
        db_user = UserInDB(
            **user.dict(), user_type="doctor", hashed_password=hashed_password
        )
        success = await self.repository.create_user(db_user)
        if not success:
            raise UserAlreadyExistsException
        return DoctorResponse(**user.dict())

    async def delete_user(self, email: str, current_user: UserInDB):
        if current_user.email != email:
            raise NotAuthorizedException
        success = await self.repository.delete_user(email)
        if not success:
            raise UserNotFoundException
        return {"message": "User deleted successfully"}

    async def get_all_doctors(self) -> List[DoctorResponse]:
        return await self.repository.get_all_doctors()
