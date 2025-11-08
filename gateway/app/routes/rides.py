from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..schemas import RideResponse, RideCreate
from ..database import get_db
from ..models import User, Ride
from sqlalchemy.orm import Session
from ..auth import get_current_user
import redis
import os
import json

router = APIRouter(prefix="/rides", tags=["Rides"])
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"), 
    port=int(os.getenv("REDIS_PORT")),
    decode_responses=True
)

@router.post("/", response_model=RideResponse)
def create_ride(ride: RideCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.is_driver:
        raise HTTPException(status_code=403, detail="Driver cannot request a ride")
    db_ride = Ride(
        user_id=current_user.id,
        pickup=ride.pickup,
        dropoff=ride.dropoff,
        status="requested",
    )
    db.add(db_ride)
    db.commit()
    db.refresh(db_ride)

    # Add ride to processing queue
    ride_payload = {"ride_id": db_ride.id}
    redis_client.lpush("ride_queue", json.dumps(ride_payload))
    
    # Broadcast ride creation to all connected drivers via WebSocket
    driver_notification = {
        "type": "ride_created",
        "event": "new_ride",
        "ride_id": db_ride.id,
        "user_id": current_user.id,
        "pickup": db_ride.pickup,
        "dropoff": db_ride.dropoff,
        "status": db_ride.status,
        "created_at": db_ride.created_at.isoformat() if db_ride.created_at else None,
        "broadcast_to_drivers": True  # Flag to broadcast only to drivers
    }
    redis_client.publish("ride_updates", json.dumps(driver_notification))
    
    return db_ride


@router.get('/', response_model=List[RideResponse])
def get_all_rides(db: Session = Depends(get_db)):
    rides = db.query(Ride).all()
    return rides


@router.get("/{ride_id}/assign", response_model=RideResponse)
def assign_ride(ride_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_driver:
        raise HTTPException(status_code=403, detail="Only drivers can assign rides")
    db_ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not db_ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if db_ride.status != "requested":
        raise HTTPException(status_code=400, detail="Ride already assigned or completed")
    db_ride.driver_id = current_user.id
    db_ride.status = "assigned"
    db.commit()
    db.refresh(db_ride)
    return db_ride


@router.post("/{ride_id}/complete", response_model=RideResponse)
def complete_ride(ride_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_driver:
        raise HTTPException(status_code=403, detail="Only drivers can complete rides")
    db_ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not db_ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if db_ride.status != "assigned":
        raise HTTPException(status_code=400, detail="Ride not assigned to driver")
    db_ride.status = "completed"
    db.commit()
    payload = {
        "type": "ride_completed",
        "ride_id": db_ride.id,
        "user_id": db_ride.user_id,
        "driver_id": db_ride.driver_id,
        "status": db_ride.status
    }
    redis_client.publish("ride_updates", json.dumps(payload))
    db.refresh(db_ride)
    return db_ride


@router.get("/my", response_model=List[RideResponse])
def get_my_rides(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rides = db.query(Ride).filter(Ride.user_id == current_user.id).all()
    return rides


@router.get("/assigned", response_model=List[RideResponse])
def get_assigned_ride(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_driver:
        raise HTTPException(status_code=403, detail="Only drivers can view assigned rides")
    rides = db.query(Ride).filter(Ride.driver_id == current_user.id).all()
    return rides


@router.get("/{ride_id}/assign", response_model=RideResponse)
async def assign_ride(ride_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_driver:
        raise HTTPException(status_code=403, detail="Only drivers can assign rides")
    
    db_ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not db_ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if db_ride.status != "requested":
        raise HTTPException(status_code=400, detail="Ride already assigned or completed")

    db_ride.driver_id = current_user.id
    db_ride.status = "assigned"
    db.commit()
    db.refresh(db_ride)

    from ..ws_manager import send_to_user
    send_to_user(db_ride.user_id, {
        "event": "ride_accept",
        "ride_id": db_ride.id,
        "driver_id": current_user.id,
        "status": "assigned"
    })
    return db_ride
