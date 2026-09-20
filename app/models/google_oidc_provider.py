from pydantic import BaseModel, HttpUrl


class GoogleOIDCProviderMetadata(BaseModel):
    issuer: HttpUrl
    authorization_endpoint: HttpUrl
    token_endpoint: HttpUrl
    jwks_uri: HttpUrl
