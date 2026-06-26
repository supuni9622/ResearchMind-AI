# Health endpoint models.

from pydantic import BaseModel


class LiveResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str


class HealthServices(BaseModel):
    postgres: str
    valkey: str
    qdrant: str


class HealthStatus(BaseModel):
    status: str
    services: HealthServices
