import sys
import os

# Add /app to Python path
sys.path.append("/app/gateway")

from dotenv import load_dotenv
from sqlalchemy.orm import Session
from app import models, database
import json
import time

load_dotenv()

# Optional Redis setup
redis_client = None
REDIS_AVAILABLE = False

try:
    import redis
    redis_host = os.getenv("REDIS_HOST")
    redis_port = os.getenv("REDIS_PORT")
    
    if redis_host and redis_port:
        redis_client = redis.Redis(
            host=redis_host,
            port=int(redis_port),
            socket_connect_timeout=2
        )
        redis_client.ping()
        REDIS_AVAILABLE = True
        print("[Worker] Redis connected for queue management")
    else:
        print("[Worker] Redis not configured, using database polling")
except Exception as e:
    print(f"[Worker] Redis not available: {e}. Using database polling instead.")

MAX_RETRIES = 5
RETRY_DELAY = 5
PROCESSED_RIDES = set()  # In-memory set for processed rides (if no Redis)


def assign_driver(db: Session, ride_id: int):
    try:
        driver = db.query(models.User).filter(models.User.is_driver == True).first()
        if not driver:
            print("No driver available")
            return False
        
        db_ride = db.query(models.Ride).filter(models.Ride.id == ride_id).first()
        if not db_ride:
            print(f"Ride {ride_id} not found")
            return False
        
        if db_ride.status != "requested":
            print(f"Ride {ride_id} already processed (status: {db_ride.status})")
            return True  # Already processed
        
        db_ride.driver_id = driver.id
        db_ride.status = "assigned"
        db.commit()
        
        # Try to notify via Redis if available
        if REDIS_AVAILABLE and redis_client:
            try:
                payload = {
                    "type": "ride_assigned",
                    "ride_id": db_ride.id,
                    "user_id": db_ride.user_id,
                    "driver_id": db_ride.driver_id,
                    "status": db_ride.status
                }
                redis_client.publish("ride_updates", json.dumps(payload))
            except Exception as e:
                print(f"[Worker] Failed to publish to Redis: {e}")
        
        print(f"Driver {driver.id} assigned to ride {ride_id}")
        return True
    except Exception as e:
        db.rollback()
        print(f"Error assigning driver to ride {ride_id}: {e}")
        return False


def process_ride(ride_data: dict):
    ride_id = ride_data.get("ride_id")
    if not ride_id:
        print("No ride ID found")
        return False
    
    # Check if already processed
    if ride_id in PROCESSED_RIDES:
        print(f"Ride {ride_id} already processed")
        return True
    
    db = next(database.get_db())
    success = False
    try:
        for attempt in range(1, MAX_RETRIES + 1):
            success = assign_driver(db, ride_id)
            if success:
                PROCESSED_RIDES.add(ride_id)
                break
            else:
                time.sleep(RETRY_DELAY)
        
        if not success:
            print(f"Failed to assign driver to ride {ride_id} after {MAX_RETRIES} attempts")
            return False
        return True
    finally:
        db.close()


if __name__ == "__main__":
    print("Worker started, listening for ride requests...")
    
    if REDIS_AVAILABLE:
        print("[Worker] Using Redis queue")
        # Redis-based queue processing
        while True:
            try:
                ride = redis_client.blpop("ride_queue", timeout=5)
                if ride:
                    ride_data = json.loads(ride[1])
                    ride_id = ride_data.get("ride_id")
                    
                    # Check if already processed (using Redis set if available)
                    try:
                        if redis_client.sismember("ride_queue:processed", ride_id):
                            print(f"Ride {ride_id} already processed")
                            continue
                    except:
                        pass  # Redis set not available, use in-memory
                    
                    process_ride(ride_data)
                else:
                    time.sleep(1)
            except Exception as e:
                print(f"Error processing ride from Redis queue: {e}")
                time.sleep(5)
    else:
        print("[Worker] Using database polling (no Redis)")
        # Database polling mode - check for unassigned rides
        while True:
            try:
                db = next(database.get_db())
                try:
                    # Find rides that are requested but not assigned
                    unassigned_rides = db.query(models.Ride).filter(
                        models.Ride.status == "requested",
                        models.Ride.driver_id == None
                    ).limit(10).all()
                    
                    for ride in unassigned_rides:
                        ride_id = ride.id
                        if ride_id not in PROCESSED_RIDES:
                            print(f"Processing ride {ride_id} from database")
                            process_ride({"ride_id": ride_id})
                    
                    if not unassigned_rides:
                        time.sleep(5)  # No rides, wait longer
                    else:
                        time.sleep(2)  # Processed some rides, check again soon
                finally:
                    db.close()
            except Exception as e:
                print(f"Error in database polling: {e}")
                time.sleep(5)
