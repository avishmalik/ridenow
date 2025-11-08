# ✅ Render.com Deployment Checklist

## Pre-Deployment

- [x] Updated `requirements.txt` - Removed `pymysql`, kept `psycopg2-binary`
- [x] Updated `database.py` - Supports both DATABASE_URL and individual env vars
- [x] Created `render.yaml` - Blueprint configuration
- [x] Created `Procfile` - Process definitions
- [x] Created `runtime.txt` - Python version
- [x] Created `.renderignore` - Exclude unnecessary files
- [x] Updated frontend JS - Auto-detect base URL and WebSocket protocol
- [ ] Push all changes to GitHub

## Render.com Setup Steps

### 1. Create PostgreSQL Database
- [ ] Go to Render Dashboard → New + → PostgreSQL
- [ ] Name: `ridenow-db`
- [ ] Database: `ridenow`
- [ ] Plan: Free
- [ ] Copy connection details

### 2. Deploy Web Service

**Note**: Redis is optional. The application works without Redis.
- [ ] Go to Render Dashboard → New + → Web Service
- [ ] Connect GitHub repository
- [ ] Name: `ridenow-backend`
- [ ] Environment: Python 3
- [ ] Build Command: `pip install -r requirements.txt`
- [ ] Start Command: `uvicorn gateway.app.main:app --host 0.0.0.0 --port $PORT`
- [ ] Add environment variables (see below)
- [ ] Deploy

### 3. Deploy Worker Service
- [ ] Go to Render Dashboard → New + → Background Worker
- [ ] Connect same GitHub repository
- [ ] Name: `ridenow-worker`
- [ ] Environment: Python 3
- [ ] Build Command: `pip install -r requirements.txt`
- [ ] Start Command: `python worker/ride_worker.py`
- [ ] Add environment variables (same as web service)
- [ ] Deploy

## Environment Variables

### For Web Service:
```
DATABASE_URL=<auto-filled from database>
POSTGRES_HOST=<auto-filled from database>
POSTGRES_PORT=5432
POSTGRES_USER=<auto-filled from database>
POSTGRES_PASSWORD=<auto-filled from database>
POSTGRES_DB=ridenow
REDIS_HOST= (leave empty - optional)
REDIS_PORT= (leave empty - optional)
SECRET_KEY=<generate random string>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### For Worker Service:
```
DATABASE_URL=<same as web>
POSTGRES_HOST=<same as web>
POSTGRES_PORT=5432
POSTGRES_USER=<same as web>
POSTGRES_PASSWORD=<same as web>
POSTGRES_DB=ridenow
REDIS_HOST= (leave empty - optional)
REDIS_PORT= (leave empty - optional)
```

## Post-Deployment Verification

- [ ] Check web service logs - Should see "Database tables created successfully"
- [ ] Check worker service logs - Should see "Worker started" and "Using database polling"
- [ ] Test health endpoint: `https://your-app.onrender.com/health`
- [ ] Test API docs: `https://your-app.onrender.com/docs`
- [ ] Test login/signup functionality
- [ ] Test WebSocket connection
- [ ] Test ride creation
- [ ] Test driver assignment

## Quick Commands

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Test database connection locally (if you have PostgreSQL)
psql -h <host> -U <user> -d ridenow
```

## Notes

- Free tier services spin down after 15 min inactivity
- First request after spin-down takes ~30 seconds
- WebSocket uses `wss://` protocol on Render (HTTPS)
- All frontend URLs auto-detect (no hardcoding needed)

