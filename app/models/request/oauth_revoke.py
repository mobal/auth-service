from aws_lambda_powertools import Logger
from fastapi import Form
from pydantic import BaseModel

logger = Logger()


class OAuthRevokeRequest(BaseModel):
    token: str

    @classmethod
    def as_form(cls, token: str = Form(...)) -> "OAuthRevokeRequest":
        logger.debug("Building OAuthRevokeRequest from form data")
        return cls(token=token)
