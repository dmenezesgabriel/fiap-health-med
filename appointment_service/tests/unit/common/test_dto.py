from datetime import datetime

from src.common.dto import Appointment


def test_valid_appointment():
    appointment = Appointment(
        doctor_email="doctor@example.com",
        patient_email="patient@example.com",
        date_time="2023-05-01 14:30:00",
    )
    assert appointment.doctor_email == "doctor@example.com"
    assert appointment.patient_email == "patient@example.com"
    assert appointment.date_time == "2023-05-01 14:30:00"


def test_date_time_parsing():
    appointment = Appointment(
        doctor_email="doctor@example.com",
        patient_email="patient@example.com",
        date_time="2023-05-01 14:30:00",
    )
    parsed_date_time = datetime.strptime(
        appointment.date_time, "%Y-%m-%d %H:%M:%S"
    )
    assert parsed_date_time.year == 2023
    assert parsed_date_time.month == 5
    assert parsed_date_time.day == 1
    assert parsed_date_time.hour == 14
    assert parsed_date_time.minute == 30
    assert parsed_date_time.second == 0
