from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Payload used to create an account."""

    display_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("display_name", mode="before")
    @classmethod
    def strip_display_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class LoginRequest(BaseModel):
    """Payload used to authenticate an existing account."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    """Bearer token returned by successful authentication."""

    access_token: str
    token_type: str = "bearer"


class PlanResponse(BaseModel):
    """Public plan data displayed by the pricing UI."""

    slug: str
    name: str
    description: str
    monthly_price: str
    emoji: str


class CheckoutRequest(BaseModel):
    """Payload used to record a chosen plan after simulated checkout."""

    plan_slug: str = Field(pattern="^(basic|standard|premium)$")
    start_trial: bool = False


class SubscriptionResponse(BaseModel):
    """Current subscription details shown in the authenticated profile."""

    plan_slug: str
    plan_name: str
    status: str
    is_trial: bool
    emoji: str
    created_at: datetime


class MeResponse(BaseModel):
    """Authenticated user profile with its current subscription, if present."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    email: EmailStr
    subscription: SubscriptionResponse | None = None
