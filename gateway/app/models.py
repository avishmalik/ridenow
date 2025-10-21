from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_driver = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rides = relationship("Ride", back_populates="user", foreign_keys='Ride.user_id')
    assigned_rides = relationship("Ride", back_populates="driver", foreign_keys='Ride.driver_id')


class Ride(Base):
    __tablename__ = "rides"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    pickup = Column(String(500), nullable=False)
    dropoff = Column(String(500), nullable=False)
    status = Column(String(50), default="requested")  # requested, assigned, completed
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="rides", foreign_keys=[user_id])
    driver = relationship("User", back_populates="assigned_rides", foreign_keys=[driver_id])