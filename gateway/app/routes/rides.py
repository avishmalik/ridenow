from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..schemas import RideResponse, RideCreate
from ..database import get_db
from ..models import User, Ride
from sqlalchemy.orm import Session
from ..auth import get_current_user

router = APIRouter(prefix="/rides", tags=["Rides"])


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


@router.get("/my", response_model=List[RideResponse])
def get_my_rides(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rides = db.query(Ride).filter(Ride.user_id == current_user.id).all()
    return rides
