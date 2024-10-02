from abc import ABC, abstractmethod
from typing import List, Optional

from src.common.dto import DoctorResponse, UserInDB


class AuthRepositoryPort(ABC):
    @abstractmethod
    async def get_user(self, email: str) -> Optional[UserInDB]:
        pass

    @abstractmethod
    async def create_user(self, user: UserInDB) -> bool:
        pass

    @abstractmethod
    async def delete_user(self, email: str) -> bool:
        pass

    @abstractmethod
    async def get_all_doctors(self) -> List[DoctorResponse]:
        pass
