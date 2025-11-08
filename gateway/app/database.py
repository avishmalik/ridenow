from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Support both PostgreSQL (Render) and MySQL (local dev)
# Render provides DATABASE_URL, local dev uses individual env vars
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Render provides DATABASE_URL in format: postgresql://user:pass@host:port/dbname
    # Convert to postgresql+psycopg2:// format if needed
    if DATABASE_URL.startswith("postgresql://"):
        SQLALCHEMY_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    else:
        SQLALCHEMY_DATABASE_URL = DATABASE_URL
    print("[Database] Using PostgreSQL from DATABASE_URL")
else:
    # Check if MySQL is configured (for local development)
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DB = os.getenv("MYSQL_DB")
    MYSQL_HOST = os.getenv("MYSQL_HOST")
    MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
    
    if MYSQL_USER and MYSQL_PASSWORD and MYSQL_DB and MYSQL_HOST:
        # Use MySQL for local development
        SQLALCHEMY_DATABASE_URL = (
            f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
            f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
        )
        print(f"[Database] Using MySQL at {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}")
    else:
        # Fallback to PostgreSQL with defaults
        POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
        POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
        POSTGRES_DB = os.getenv("POSTGRES_DB", "ridenow")
        POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
        POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
        
        SQLALCHEMY_DATABASE_URL = (
            f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
            f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        )
        print(f"[Database] Using PostgreSQL at {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
