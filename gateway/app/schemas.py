from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# User Schemas
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    is_driver: Optional[bool] = False

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    is_driver: bool

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str

# Ride Schemas
class RideBase(BaseModel):
    pickup: str
    dropoff: str


class RideCreate(RideBase):
    pass


class RideResponse(RideBase):
    id: int
    user_id: int
    driver_id: Optional[int] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
