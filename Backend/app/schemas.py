from typing import Literal
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator
from app.security import normalize_phone


ALLOWED_ROLES = {"artist", "dj", "broadcaster", "promoter", "fan", "collaborator"}


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
        if not value.isascii() or not value.isdigit() or not 4 <= len(value) <= 6:
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
        if not value.isascii() or not value.isdigit() or not 4 <= len(value) <= 6:
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
        if not value.isascii() or not value.isdigit() or not 4 <= len(value) <= 6:
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


class TrackCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    artist_name: str | None = Field(default=None, max_length=200)
    genre: str = Field(min_length=1, max_length=100)
    duration_seconds: int | None = Field(default=None, ge=0)
    audio_url: str | None = Field(default=None, max_length=2048)
    file_path: str | None = Field(default=None, max_length=2048)

    @field_validator("title", "genre", "artist_name", "audio_url", "file_path")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if value is not None else value

    @model_validator(mode="after")
    def track_location_required(self):
        if not self.audio_url and not self.file_path:
            raise ValueError("audio_url or file_path is required")
        return self


class BroadcastExecuteIn(BaseModel):
    track_id: int = Field(gt=0)
    destination_id: int | None = Field(default=None, gt=0)
    destination_ids: list[int] | None = Field(default=None, min_length=1, max_length=50)
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("destination_ids")
    @classmethod
    def valid_destination_ids(cls, value):
        if value is not None and (any(item <= 0 for item in value) or len(set(value)) != len(value)):
            raise ValueError("destination_ids must contain unique positive IDs")
        return value

    @field_validator("note")
    @classmethod
    def strip_note(cls, value):
        return value.strip() if value is not None else value

    @model_validator(mode="after")
    def destination_required(self):
        if (self.destination_id is None) == (self.destination_ids is None):
            raise ValueError("provide either destination_id or destination_ids")
        return self


class BroadcastStatusIn(BaseModel):
    status: Literal["delivered", "played", "declined"]
