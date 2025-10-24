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

MAX_RETRIES = 5
RETRY_DELAY = 5
PROCESSED_KEY = "ride_queue:processed"
FAILED_KEY = "ride_queue:failed"


def assign_driver(db: Session, ride_id: int):
    try:
        driver = db.query(models.User).filter(models.User.is_driver == True).first()
        if not driver:
            print("No driver available")
            return
        
        db_ride = db.query(models.Ride).filter(models.Ride.id == ride_id).first()
        db_ride.driver_id = driver.id
        db_ride.status = "assigned"
        db.commit()
        payload = {
            "type": "ride_assigned",
            "ride_id": db_ride.id,
            "user_id": db_ride.user_id,
            "driver_id": db_ride.driver_id,
            "status": db_ride.status
        }
        redis_client.publish("ride_updates", json.dumps(payload))
        print(f"Driver {driver.id} assigned to ride {ride_id}")
        return driver
    except Exception:
        db.rollback()
        print(f"Error assigning driver to ride {ride_id}")
        return False

def process_ride(ride_data: dict):
    ride_id = ride_data["ride_id"]
    if not ride_id:
        print("No ride ID found")
        return False
    db = next(database.get_db())
    success = False
    for attempt in range(1, MAX_RETRIES + 1):
        success = assign_driver(db, ride_id)
        if success:
            redis_client.sadd(PROCESSED_KEY, ride_id)
            break
        else:
            redis_client.sadd(FAILED_KEY, ride_id)
            time.sleep(RETRY_DELAY)
    if not success:
        print(f"Failed to assign driver to ride {ride_id} after {MAX_RETRIES} attempts")
        return False
    return True


if __name__ == "__main__":
    db = next(database.get_db())
    print("Worker started, listening for ride requests...")
    while True:
        try:
            ride = redis_client.blpop("ride_queue", timeout=5)
            if ride:
                ride_data = json.loads(ride[1])
                ride_id = ride_data["ride_id"]
                if redis_client.sismember(PROCESSED_KEY, ride_id):
                    print(f"Ride {ride_id} already processed")
                    continue
                process_ride(ride_data)
            else:
                time.sleep(1)
        except Exception as e:
            print(f"Error processing ride: {e}")
            time.sleep(5)
            
