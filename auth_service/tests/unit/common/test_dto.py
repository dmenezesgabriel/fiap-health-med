import pytest
from pydantic import ValidationError
from src.common.dto import (
    DoctorCreate,
    DoctorResponse,
    PatientCreate,
    PatientResponse,
    Token,
    TokenData,
    UserBase,
    UserInDB,
)


def test_user_base():
    user = UserBase(
        email="test@example.com", name="Test User", cpf="12345678900"
    )
    assert user.email == "test@example.com"
    assert user.name == "Test User"
    assert user.cpf == "12345678900"


def test_patient_create():
    patient = PatientCreate(
        email="patient@example.com",
        name="Patient",
        cpf="12345678900",
        password="securepass",
    )
    assert patient.email == "patient@example.com"
    assert patient.name == "Patient"
    assert patient.cpf == "12345678900"
    assert patient.password == "securepass"


def test_doctor_create():
    doctor = DoctorCreate(
        email="doctor@example.com",
        name="Doctor",
        cpf="98765432100",
        password="doctorpass",
        crm="CRM12345",
    )
    assert doctor.email == "doctor@example.com"
    assert doctor.name == "Doctor"
    assert doctor.cpf == "98765432100"
    assert doctor.password == "doctorpass"
    assert doctor.crm == "CRM12345"


def test_patient_response():
    patient = PatientResponse(
        email="patient@example.com", name="Patient", cpf="12345678900"
    )
    assert patient.email == "patient@example.com"
    assert patient.name == "Patient"
    assert patient.cpf == "12345678900"
    assert patient.user_type == "patient"


def test_doctor_response():
    doctor = DoctorResponse(
        email="doctor@example.com",
        name="Doctor",
        cpf="98765432100",
        crm="CRM12345",
    )
    assert doctor.email == "doctor@example.com"
    assert doctor.name == "Doctor"
    assert doctor.cpf == "98765432100"
    assert doctor.user_type == "doctor"
    assert doctor.crm == "CRM12345"


def test_user_in_db_patient():
    user = UserInDB(
        email="patient@example.com",
        name="Patient",
        cpf="12345678900",
        user_type="patient",
        hashed_password="hashedpass",
    )
    assert user.email == "patient@example.com"
    assert user.name == "Patient"
    assert user.cpf == "12345678900"
    assert user.user_type == "patient"
    assert user.hashed_password == "hashedpass"
    assert user.crm is None


def test_user_in_db_doctor():
    user = UserInDB(
        email="doctor@example.com",
        name="Doctor",
        cpf="98765432100",
        user_type="doctor",
        hashed_password="hashedpass",
        crm="CRM12345",
    )
    assert user.email == "doctor@example.com"
    assert user.name == "Doctor"
    assert user.cpf == "98765432100"
    assert user.user_type == "doctor"
    assert user.hashed_password == "hashedpass"
    assert user.crm == "CRM12345"


def test_token_data():
    token_data = TokenData(email="user@example.com")
    assert token_data.email == "user@example.com"


def test_token_data_optional_email():
    token_data = TokenData()
    assert token_data.email is None


def test_token():
    token = Token(access_token="some_access_token", token_type="bearer")
    assert token.access_token == "some_access_token"
    assert token.token_type == "bearer"
