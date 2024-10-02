from pydantic import BaseModel


class Appointment(BaseModel):
    doctor_email: str
    patient_email: str
    date_time: str
