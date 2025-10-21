from fastapi import FastAPI, HTTPException, Depends, status
from dotenv import load_dotenv
from . import models, database, schemas, auth
from sqlalchemy.orm import Session
import redis
import os
import json
import time

load_dotenv()

app = FastAPI(title="RideNow API")

redis_client = redis.Redis(host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")))

# Initialize database tables with retry logic
def init_db():
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            models.Base.metadata.create_all(bind=database.engine)
            print("Database tables created successfully")
            break
        except Exception as e:
            print(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print("Failed to connect to database after all retries")
                raise

# Initialize database on startup
init_db()


@app.post("/signup", response_model=schemas.UserOut)
def signup(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    hashed_password = auth.hash_password(user.password)
    db_user = models.User(name=user.name, email=user.email, password_hash=hashed_password, is_driver=user.is_driver)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/login", response_model=schemas.LoginResponse)
def login(login_data: schemas.LoginRequest, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.email == login_data.email).first()
    if not db_user or not auth.verify_password(login_data.password, db_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = auth.create_access_token({"sub": str(db_user.id)})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/rides", response_model=schemas.RideOut)
def request_ride(ride: schemas.RideCreate, user_id: int, db: Session = Depends(database.get_db)):
    db_ride = models.Ride(user_id=user_id, pickup=ride.pickup, dropoff=ride.dropoff)
    db.add(db_ride)
    db.commit()
    db.refresh(db_ride)

    ride_data = {"ride_id": db_ride.id, "user_id": user_id, "pickup": ride.pickup, "dropoff": ride.dropoff}
    redis_client.rpush("ride_queue", json.dumps(ride_data))
    return db_ride

@app.get("/rides/{ride_id}", response_model=schemas.RideOut)
def get_ride(ride_id: int, db: Session = Depends(database.get_db)):
    db_ride = db.query(models.Ride).filter(models.Ride.id == ride_id).first()
    if not db_ride:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ride not found")
    return db_ride

@app.get("/")
def read_root():
    return {"message": "RideNow API is running!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
