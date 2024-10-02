from abc import ABC, abstractmethod

from src.common.dto import (
    AvailabilityDelete,
    AvailabilityUpdate,
    DailyAvailability,
)


class AvailabilityRepositoryPort(ABC):
    @abstractmethod
    async def add_availability(self, availability: DailyAvailability) -> bool:
        pass

    @abstractmethod
    async def get_doctor_availability(self, doctor_email: str) -> dict:
        pass

    @abstractmethod
    async def update_availability(
        self, doctor_email: str, update: AvailabilityUpdate
    ) -> bool:
        pass

    @abstractmethod
    async def delete_availability(
        self, doctor_email: str, delete: AvailabilityDelete
    ) -> bool:
        pass
