import httpx
from app.models import Cache, Token


import logging
from typing import Optional

from starlette import status

from app.settings import Settings


class CacheService:
    def __init__(self):
        self.logger = logging.getLogger()
        self.settings = Settings()

    async def get(self, key: str) -> Optional[Cache]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{self.settings.cache_service_base_url}/api/cache/{key}')
        if response.status_code == status.HTTP_200_OK:
            return Cache.parse_obj(response.json())
        return None


class AuthService:
    async def create_user(self, user_data: dict):
        pass

    async def login(self, email: str, password: str) -> Token:
        return Token(
            token='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaW'
            'F0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c')

    async def logout(self) -> bool:
        return True
