from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=1, max_length=50)

    @field_validator("display_name")
    @classmethod
    def strip_display_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Имя не может быть пустым")
        return stripped


class LoginRequest(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)
