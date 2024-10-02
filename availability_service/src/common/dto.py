from typing import List, Optional

from pydantic import BaseModel, EmailStr


class TimeSlot(BaseModel):
    start_time: str
    end_time: str


class DailyAvailability(BaseModel):
    doctor_email: EmailStr
    day: str
    time_slots: List[TimeSlot]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "doctor_email": "doctor@example.com",
                    "day": "2023-05-01",
                    "time_slots": [
                        {"start_time": "09:00", "end_time": "12:00"},
                        {"start_time": "14:00", "end_time": "18:00"},
                    ],
                }
            ]
        }
    }


class AvailabilityUpdate(BaseModel):
    day: str
    old_start_time: str
    old_end_time: str
    new_start_time: Optional[str] = None
    new_end_time: Optional[str] = None


class AvailabilityDelete(BaseModel):
    day: str
    start_time: str
    end_time: str
