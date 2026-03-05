from pydantic import EmailStr, ValidationInfo, constr, field_validator

from app.models.models import CamelModel


class RegistrationRequest(CamelModel):
    email: EmailStr
    username: str
    password: constr(min_length=8)
    confirm_password: str
    display_name: str | None = None

    @field_validator("confirm_password", mode="after")
    @classmethod
    def passwords_match(cls, value: str, validation_info: ValidationInfo) -> str:
        if (
            "password" in validation_info.data
            and value != validation_info.data["password"]
        ):
            raise ValueError("Passwords do not match")
        return value
