from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: str
    last_name: str
    email: str
    role: str


class ProfileUpdate(BaseModel):
    """Self-service profile edit. Every field optional — this is a PATCH, and a
    customer changing only their surname should not have to resend a password.
    """

    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    # Changing either the email or the password requires proving the current
    # one: a hijacked session must not be able to lock the real owner out.
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=8)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
