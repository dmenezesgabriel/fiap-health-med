from src.common.dto import (
    AvailabilityDelete,
    AvailabilityUpdate,
    DailyAvailability,
    TimeSlot,
)


def test_time_slot():
    time_slot = TimeSlot(start_time="09:00", end_time="12:00")
    assert time_slot.start_time == "09:00"
    assert time_slot.end_time == "12:00"


def test_daily_availability():
    daily_availability = DailyAvailability(
        doctor_email="doctor@example.com",
        day="2023-05-01",
        time_slots=[
            TimeSlot(start_time="09:00", end_time="12:00"),
            TimeSlot(start_time="14:00", end_time="18:00"),
        ],
    )
    assert daily_availability.doctor_email == "doctor@example.com"
    assert daily_availability.day == "2023-05-01"
    assert len(daily_availability.time_slots) == 2
    assert daily_availability.time_slots[0].start_time == "09:00"
    assert daily_availability.time_slots[0].end_time == "12:00"
    assert daily_availability.time_slots[1].start_time == "14:00"
    assert daily_availability.time_slots[1].end_time == "18:00"


def test_availability_update():
    update = AvailabilityUpdate(
        day="2023-05-01",
        old_start_time="09:00",
        old_end_time="12:00",
        new_start_time="10:00",
        new_end_time="13:00",
    )
    assert update.day == "2023-05-01"
    assert update.old_start_time == "09:00"
    assert update.old_end_time == "12:00"
    assert update.new_start_time == "10:00"
    assert update.new_end_time == "13:00"


def test_availability_update_partial():
    update = AvailabilityUpdate(
        day="2023-05-01",
        old_start_time="09:00",
        old_end_time="12:00",
        new_start_time="10:00",
    )
    assert update.day == "2023-05-01"
    assert update.old_start_time == "09:00"
    assert update.old_end_time == "12:00"
    assert update.new_start_time == "10:00"
    assert update.new_end_time is None


def test_availability_delete():
    delete = AvailabilityDelete(
        day="2023-05-01", start_time="09:00", end_time="12:00"
    )
    assert delete.day == "2023-05-01"
    assert delete.start_time == "09:00"
    assert delete.end_time == "12:00"


def test_daily_availability_model_config():
    example = DailyAvailability.model_config["json_schema_extra"]["examples"][
        0
    ]
    assert example["doctor_email"] == "doctor@example.com"
    assert example["day"] == "2023-05-01"
    assert len(example["time_slots"]) == 2
    assert example["time_slots"][0] == {
        "start_time": "09:00",
        "end_time": "12:00",
    }
    assert example["time_slots"][1] == {
        "start_time": "14:00",
        "end_time": "18:00",
    }
