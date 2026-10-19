from pydantic import BaseModel, Field

EMAIL_PATTERN = r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$"


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(max_length=254, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=1, max_length=128)


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class PasswordChangeIn(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(max_length=128)


class PreferencesIn(BaseModel):
    notifications_enabled: bool
    theme: str = Field(pattern=r"^(light|dark|system)$")


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class SelectModeIn(BaseModel):
    analysis_id: int
    mode: str = Field(min_length=1, max_length=80)
