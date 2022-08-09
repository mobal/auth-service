import logging
import uuid
from typing import Optional, Any
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError

import httpx
import jwt
import pendulum
from fastapi import HTTPException
from starlette import status

from app.models import Cache, JWTToken, Token
from app.repository import UserRepository
from app.settings import Settings


class CacheService:
    def __init__(self):
        self._logger = logging.getLogger()
        self.settings = Settings()

    async def get(self, key: str) -> Optional[Cache]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.settings.cache_service_base_url}/api/cache/{key}'
            )
        if response.status_code == status.HTTP_200_OK:
            return Cache.parse_obj(response.json())
        return None

    async def put(self, key: str, value: Any, ttl: int = 0):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{self.settings.cache_service_base_url}/api/cache',
                json={'key': key, 'value': value, 'ttl': ttl},
            )
        if response.status_code == status.HTTP_201_CREATED:
            return True
        self._logger.error(f'Failed to cache key={key}, value={value}, ttl={ttl}')
        return False


class AuthService:
    USER_KEYS_TO_REMOVE = ['password']

    def __init__(self):
        self._logger = logging.getLogger()
        self.cache_service = CacheService()
        self.password_hasher = PasswordHasher()
        self.settings = Settings()
        self.user_repository = UserRepository()

    async def _generate_token(self, payload: dict) -> str:
        iat = pendulum.now()
        exp = iat.add(seconds=self.settings.jwt_token_lifetime)
        return jwt.encode(
            JWTToken(
                exp=exp.int_timestamp,
                iat=iat.int_timestamp,
                jti=str(uuid.uuid4()),
                sub=payload,
            ).dict(),
            self.settings.jwt_secret,
        )

    async def _transform_user(self, user_dict: dict) -> dict:
        for k in self.USER_KEYS_TO_REMOVE:
            user_dict.pop(k, None)
        return user_dict

    async def login(self, email: str, password: str) -> Token:
        user = await self.user_repository.get_by_email(email)
        try:
            self.password_hasher.verify(user.password, password)
            return Token(
                token=await self._generate_token(
                    await self._transform_user(user.dict())
                )
            )
        except (InvalidHash, VerifyMismatchError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid email or password',
            )

    async def logout(self, jwt_token: JWTToken):
        result = await self.cache_service.put(
            f'jti_{jwt_token.jti}', jwt_token.dict(), jwt_token.exp
        )
        if result is False:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Internal Server Error',
            )
