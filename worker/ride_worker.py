import sys
import os

# Add /app to Python path
sys.path.append("/app/gateway")

from dotenv import load_dotenv
import redis
import os
from sqlalchemy.orm import Session
from app import models, database
import json
import time

load_dotenv()

redis_client = redis.Redis(host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")))

def assign_driver(db: Session, ride_id: int):
    driver = db.query(models.User).filter(models.User.is_driver == True).first()
    if not driver:
        print("No driver available")
        return
    db.query(models.Ride).filter(models.Ride.id == ride_id).update({"driver_id": driver.id, "status": "assigned"})
    db.commit()
    print(f"Driver {driver.id} assigned to ride {ride_id}")
    return driver

if __name__ == "__main__":
    db = next(database.get_db())
    print("Worker started, listening for ride requests...")
    while True:
        ride = redis_client.blpop("ride_queue", timeout=5)
        if ride:
            ride_data = json.loads(ride[1])
            assign_driver(db, ride_data["ride_id"])
        time.sleep(1)
