import re
from datetime import datetime
from typing import Literal
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, TypeAdapter, field_validator


ALLOWED_ROLES = {"artist", "dj", "broadcaster", "promoter", "fan", "collaborator"}


def normalize_phone(value: str) -> str:
    compact = re.sub(r"[\s\-]", "", value)
    if compact.startswith("+"):
        compact = compact[1:]
    if compact.startswith("00237"):
        compact = compact[4:]
    elif compact.startswith("237"):
        compact = compact[3:]
    if re.fullmatch(r"6\d{8}", compact):
        return "+237" + compact
    raise ValueError("invalid Cameroon mobile number")


class RegisterIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(min_length=1, max_length=200)
    phone: str
    pin: str
    role: Literal["artist", "dj", "broadcaster", "promoter", "fan", "collaborator"]
    city: str = Field(min_length=1, max_length=100)

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, value):
        return normalize_phone(value)

    @field_validator("pin")
    @classmethod
    def pin_valid(cls, value):
        if not re.fullmatch(r"\d{4,6}", value):
            raise ValueError("PIN must contain 4 to 6 digits")
        return value


class LoginIn(BaseModel):
    phone: str
    pin: str

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, value):
        return normalize_phone(value)

    @field_validator("pin")
    @classmethod
    def pin_valid(cls, value):
        if not re.fullmatch(r"\d{4,6}", value):
            raise ValueError("PIN must contain 4 to 6 digits")
        return value


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str | None = Field(default=None, min_length=1, max_length=200)
    city: str | None = Field(default=None, min_length=1, max_length=100)


class ChangePinIn(BaseModel):
    old_pin: str
    new_pin: str

    @field_validator("new_pin")
    @classmethod
    def pin_valid(cls, value):
        if not re.fullmatch(r"\d{4,6}", value):
            raise ValueError("PIN must contain 4 to 6 digits")
        return value


class SocialLinks(BaseModel):
    model_config = ConfigDict(extra="forbid")
    youtube: str | None = None
    instagram: str | None = None
    tiktok: str | None = None
    facebook: str | None = None
    audiomack: str | None = None
    boomplay: str | None = None

    @field_validator("*")
    @classmethod
    def http_url(cls, value):
        if value is None:
            return value
        return str(TypeAdapter(AnyHttpUrl).validate_python(value))


class ProfileIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    display_name: str = Field(min_length=1, max_length=200)
    bio: str = Field(default="", max_length=500)
    genres: list[str] = Field(default_factory=list, max_length=5)
    photo_url: str | None = Field(default=None, max_length=2048)
    social_links: SocialLinks = Field(default_factory=SocialLinks)
    details: dict = Field(default_factory=dict)

    # Role-specific fields are also accepted at top level for a convenient API.
    stage_name: str | None = None
    manager_phone: str | None = None
    languages: list[str] | None = Field(default=None, max_length=20)
    dj_type: Literal["club", "radio", "event"] | None = None
    venues: list[str] | None = Field(default=None, max_length=50)
    station_name: str | None = Field(default=None, min_length=1, max_length=200)
    medium: Literal["radio", "tv"] | None = None
    frequency: str | None = Field(default=None, max_length=50)
    coverage_cities: list[str] | None = Field(default=None, max_length=50)
    company_name: str | None = Field(default=None, min_length=1, max_length=200)
    venue_names: list[str] | None = Field(default=None, max_length=50)

    @field_validator("genres")
    @classmethod
    def normalize_genres(cls, value):
        if len(value) > 5:
            raise ValueError("genres cannot contain more than 5 items")
        return [item.strip().lower() for item in value if item.strip()]

    @field_validator("photo_url")
    @classmethod
    def photo_http(cls, value):
        if value is None:
            return value
        return str(TypeAdapter(AnyHttpUrl).validate_python(value))

    @field_validator("display_name", "stage_name", "station_name", "company_name")
    @classmethod
    def strip_names(cls, value):
        return value.strip() if value is not None else value

    @field_validator("manager_phone")
    @classmethod
    def normalize_manager_phone(cls, value):
        return normalize_phone(value) if value is not None else value


class VerificationRequestIn(BaseModel):
    evidence_text: str = Field(min_length=1, max_length=5000)
    evidence_url: str | None = None

    @field_validator("evidence_url")
    @classmethod
    def evidence_http(cls, value):
        if value is None:
            return value
        return str(TypeAdapter(AnyHttpUrl).validate_python(value))


class VerificationDecisionIn(BaseModel):
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=2000)


class TicketCreateIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_name: str = Field(min_length=1, max_length=200)
    event_id: int | None = Field(default=None, ge=1)
    total_quantity: int = Field(ge=1, le=10000)
    price_xaf: int = Field(default=0, ge=0, le=100000000)
    description: str | None = None

    @field_validator("event_name")
    @classmethod
    def event_name_not_blank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("event_name cannot be blank")
        return value

    @field_validator("price_xaf")
    @classmethod
    def validate_paid_price(cls, value):
        if value != 0 and value < 100:
            raise ValueError("price_xaf must be 0 or at least 100 XAF")
        return value


class TicketOut(BaseModel):
    id: int
    event_id: int | None = None
    event_name: str
    total_quantity: int
    remaining_quantity: int
    price_xaf: int = 0
    status: str
    description: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TicketPaymentOut(BaseModel):
    id: int
    ticket_id: int
    reference: str
    amount_xaf: int
    status: str
    checkout_url: str | None = None
    created_at: datetime


class EventCreateIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    event_date: datetime | None = None
    venue: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, max_length=100)

    @field_validator("event_name")
    @classmethod
    def event_name_not_blank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("event_name cannot be blank")
        return value


class EventOut(BaseModel):
    id: int
    artist_id: int
    event_name: str
    description: str | None = None
    event_date: datetime | None = None
    venue: str | None = None
    city: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventCollaboratorIn(BaseModel):
    user_id: int = Field(ge=1)


class EventCollaboratorOut(BaseModel) :
    user_id: int
    name: str
    created_at: datetime
