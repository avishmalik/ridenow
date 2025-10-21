from pydantic import BaseModel
from typing import Optional

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
        orm_mode = True

# Ride Schemas
class RideCreate(BaseModel):
    pickup: str
    dropoff: str

class RideOut(BaseModel):
    id: int
    user_id: int
    driver_id: Optional[int]
    pickup: str
    dropoff: str
    status: str

    class Config:
        orm_mode = True
