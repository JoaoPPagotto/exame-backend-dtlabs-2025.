from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    username: str
    password: str

class SensorDataCreate(BaseModel):
    server_ulid: str
    server_name: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    voltage: Optional[float] = None
    current: Optional[float] = None

class SensorDataResponse(BaseModel):
    server_ulid: str
    server_name: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    voltage: Optional[float] = None
    current: Optional[float] = None
    timestamp: datetime

    class Config:
        orm_mode = True

class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True
