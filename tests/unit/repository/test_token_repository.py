import pytest

from app.models import JWTToken
from app.repositories import TokenRepository


@pytest.mark.asyncio
class TestTokenRepository:
    async def test_successfully_get_by_id(
        self,
        jwt_token: JWTToken,
        refresh_token: str,
        token_repository: TokenRepository,
        tokens_table,
    ):
        item = await token_repository.get_by_id(jwt_token.jti)

        assert item == (jwt_token, refresh_token)
