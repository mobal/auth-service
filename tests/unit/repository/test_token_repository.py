import pytest

from app.models import JWTToken
from app.repositories import TokenRepository


@pytest.mark.asyncio
class TestTokenRepository:
    async def test_successfully_get_by_id(
        self,
        jwt_token: JWTToken,
        refresh_token: JWTToken,
        token_repository: TokenRepository,
        tokens_table,
    ):
        item = await token_repository.get_by_id(refresh_token.sub["jti"])

        assert item == {
            "jti": jwt_token.jti,
            "jwt_token": jwt_token.model_dump(),
            "refresh_token": refresh_token.model_dump(),
            "ttl": jwt_token.exp,
        }
