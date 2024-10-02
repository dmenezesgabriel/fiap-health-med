from src.common.dto import (
    AvailabilityDelete,
    AvailabilityUpdate,
    DailyAvailability,
)
from src.ports.availability_repository import AvailabilityRepositoryPort


class AvailabilityService:
    def __init__(self, repository: AvailabilityRepositoryPort):
        self.repository = repository

    async def add_availability(self, availability: DailyAvailability):
        return await self.repository.add_availability(availability)

    async def get_doctor_availability(self, doctor_email: str):
        return await self.repository.get_doctor_availability(doctor_email)

    async def update_availability(
        self, doctor_email: str, update: AvailabilityUpdate
    ):
        return await self.repository.update_availability(doctor_email, update)

    async def delete_availability(
        self, doctor_email: str, delete: AvailabilityDelete
    ):
        return await self.repository.delete_availability(doctor_email, delete)
