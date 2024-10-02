from datetime import timedelta
from typing import List, Union

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordRequestForm,
)
from src.common.dto import (
    DoctorCreate,
    DoctorResponse,
    PatientCreate,
    PatientResponse,
    Token,
    UserInDB,
)
from src.domain.exceptions import (
    InvalidCredentialsException,
    NotAuthorizedException,
    UserAlreadyExistsException,
    UserNotFoundException,
)
from src.domain.services.auth_service import AuthService
from src.infrastructure.database.dynamodb_auth_repository import (
    DynamoDBAuthRepository,
)

ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter()
security = HTTPBearer()


def get_auth_service():
    repository = DynamoDBAuthRepository()
    return AuthService(repository)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        token_data = auth_service.decode_token(credentials.credentials)
        user = await auth_service.repository.get_user(email=token_data.email)
        if user is None:
            raise UserNotFoundException
        return user
    except InvalidCredentialsException:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/register/patient", response_model=PatientResponse)
async def create_patient(
    user: PatientCreate, auth_service: AuthService = Depends(get_auth_service)
):
    try:
        return await auth_service.create_patient(user)
    except UserAlreadyExistsException:
        raise HTTPException(status_code=400, detail="Email already registered")


@router.post("/register/doctor", response_model=DoctorResponse)
async def create_doctor(
    user: DoctorCreate, auth_service: AuthService = Depends(get_auth_service)
):
    try:
        return await auth_service.create_doctor(user)
    except UserAlreadyExistsException:
        raise HTTPException(status_code=400, detail="Email already registered")


@router.delete("/users/{email}")
async def delete_user(
    email: str,
    current_user: UserInDB = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        return await auth_service.delete_user(email, current_user)
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except NotAuthorizedException:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this user"
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        user = await auth_service.authenticate_user(
            form_data.username, form_data.password
        )
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_service.create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except (UserNotFoundException, InvalidCredentialsException):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/users/me", response_model=Union[PatientResponse, DoctorResponse])
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    if current_user.user_type == "patient":
        return PatientResponse(**current_user.dict())
    elif current_user.user_type == "doctor":
        return DoctorResponse(**current_user.dict())
    else:
        raise HTTPException(status_code=400, detail="Invalid user type")


@router.get("/verify-token")
async def verify_token(current_user: UserInDB = Depends(get_current_user)):
    if current_user.user_type == "patient":
        user_response = PatientResponse(**current_user.dict())
    elif current_user.user_type == "doctor":
        user_response = DoctorResponse(**current_user.dict())
    else:
        raise HTTPException(status_code=400, detail="Invalid user type")
    return {"message": "Token is valid", "user": user_response}


@router.get("/doctors", response_model=List[DoctorResponse])
async def list_doctors(auth_service: AuthService = Depends(get_auth_service)):
    return await auth_service.get_all_doctors()
