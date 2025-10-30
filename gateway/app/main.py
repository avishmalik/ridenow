from fastapi import FastAPI, HTTPException, Depends, status
from dotenv import load_dotenv
from . import models, database, schemas, auth
from sqlalchemy.orm import Session
import redis
import os
import time
from .routes import rides
from .websocket_route import router as ws_router
import asyncio
import threading
from .ws_forwarder import WsForwarder
from .ws_manager import redis_listener
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
load_dotenv()

app = FastAPI(title="RideNow API")
app.include_router(rides.router)
app.include_router(ws_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://127.0.0.1:5500"] if you’re opening HTML in browser
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = redis.Redis(host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")))

from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="gateway/app/static", html=True), name="static")

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
    print(login_data)
    db_user = db.query(models.User).filter(models.User.email == login_data.email).first()
    if not db_user or not auth.verify_password(login_data.password, db_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = auth.create_access_token({"sub": str(db_user.id)})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/")
def read_root():
    return FileResponse(os.path.join("gateway/app/static", "index.html"))


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_event_loop()
    app.state.loop = loop
    app.state.ws_forwarder = WsForwarder(loop)

    t = threading.Thread(target=redis_listener, args=(app,), daemon=True)
    t.start()
