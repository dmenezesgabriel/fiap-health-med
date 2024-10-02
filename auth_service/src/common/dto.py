from typing import Optional

from pydantic import BaseModel, EmailStr


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
