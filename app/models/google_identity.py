from pydantic import BaseModel, EmailStr


class GoogleIdentity(BaseModel):
    issuer: str
    subject: str
    email: EmailStr
    email_verified: bool
    nonce: str
