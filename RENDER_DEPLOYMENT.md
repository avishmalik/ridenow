# 🚀 RideNow Deployment Guide for Render.com

This guide will help you deploy your RideNow application on Render.com with PostgreSQL.

## 📋 Prerequisites

1. **Render.com Account**: Sign up at [render.com](https://render.com) (free tier available)
2. **GitHub Repository**: Push your code to GitHub
3. **PostgreSQL Database**: Render provides free PostgreSQL
4. **Redis**: Optional - Application works without Redis using direct WebSocket and database polling

## 🗂️ Step-by-Step Deployment

### Step 1: Prepare Your Repository

1. **Push your code to GitHub**:
   ```bash
   git add .
   git commit -m "Prepare for Render deployment"
   git push origin main
   ```

2. **Verify these files are in your repo**:
   - `requirements.txt` (with psycopg2-binary, no pymysql)
   - `render.yaml` (deployment configuration)
   - `Procfile` (process definitions)
   - `runtime.txt` (Python version)

### Step 2: Create PostgreSQL Database on Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"PostgreSQL"**
3. Configure:
   - **Name**: `ridenow-db`
   - **Database**: `ridenow`
   - **User**: `ridenow_user` (or leave default)
   - **Region**: Choose closest to you
   - **Plan**: Free
4. Click **"Create Database"**
5. **Note the connection details** (you'll need these)

### Step 3: Create Redis Instance on Render

1. In Render Dashboard, click **"New +"** → **"Redis"**
2. Configure:
   - **Name**: `ridenow-redis`
   - **Region**: Same as PostgreSQL
   - **Plan**: Free
3. Click **"Create Redis"**

### Step 4: Deploy Web Service (Backend)

1. In Render Dashboard, click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure:
   - **Name**: `ridenow-backend`
   - **Region**: Same as database
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: Leave empty (root)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn gateway.app.main:app --host 0.0.0.0 --port $PORT`
4. **Environment Variables** (Add these):
   ```
   POSTGRES_HOST=<from database>
   POSTGRES_PORT=<from database>
   POSTGRES_USER=<from database>
   POSTGRES_PASSWORD=<from database>
   POSTGRES_DB=ridenow
   REDIS_HOST= (leave empty - optional)
   REDIS_PORT= (leave empty - optional)
   SECRET_KEY=<generate a random string>
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```
5. Click **"Create Web Service"**

### Step 4: Deploy Worker Service

1. In Render Dashboard, click **"New +"** → **"Background Worker"**
2. Select the same GitHub repository
3. Configure:
   - **Name**: `ridenow-worker`
   - **Region**: Same as web service
   - **Branch**: `main`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python worker/ride_worker.py`
4. **Environment Variables** (Same as web service):
   ```
   POSTGRES_HOST=<from database>
   POSTGRES_PORT=<from database>
   POSTGRES_USER=<from database>
   POSTGRES_PASSWORD=<from database>
   POSTGRES_DB=ridenow
   REDIS_HOST= (leave empty - optional)
   REDIS_PORT= (leave empty - optional)
   ```
5. Click **"Create Background Worker"**

### Step 5: Link Services (Using render.yaml - Alternative Method)

If you prefer using `render.yaml`:

1. In Render Dashboard, click **"New +"** → **"Blueprint"**
2. Connect your GitHub repository
3. Render will automatically detect `render.yaml` and create all services
4. Review and click **"Apply"**

## 🔧 Manual Configuration (If not using render.yaml)

### Environment Variables Setup

For **Web Service**:
```bash
POSTGRES_HOST=<your-postgres-host>
POSTGRES_PORT=5432
POSTGRES_USER=<your-postgres-user>
POSTGRES_PASSWORD=<your-postgres-password>
POSTGRES_DB=ridenow
REDIS_HOST= (leave empty - optional)
REDIS_PORT= (leave empty - optional)
SECRET_KEY=<generate-random-secret>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

For **Worker Service**:
```bash
POSTGRES_HOST=<same-as-web>
POSTGRES_PORT=5432
POSTGRES_USER=<same-as-web>
POSTGRES_PASSWORD=<same-as-web>
POSTGRES_DB=ridenow
REDIS_HOST= (leave empty - optional)
REDIS_PORT= (leave empty - optional)
```

## 🌐 Update Frontend URLs

After deployment, update your frontend JavaScript files to use the Render URL:

1. **Update `gateway/app/static/js/auth.js`**:
   ```javascript
   const BASE_URL = window.location.origin; // Auto-detect
   // OR
   const BASE_URL = "https://your-app-name.onrender.com";
   ```

2. **Update `gateway/app/static/js/ws.js`**:
   ```javascript
   const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
   const wsHost = window.location.host;
   socket = new WebSocket(`${wsProtocol}//${wsHost}/ws?token=${token}`);
   ```

## ✅ Verification Steps

1. **Check Web Service Logs**:
   - Go to your web service → Logs
   - Look for: "Database tables created successfully"
   - Look for: "Application startup complete"

2. **Check Worker Logs**:
   - Go to your worker service → Logs
   - Look for: "Worker started, listening for ride requests..."

3. **Test API**:
   - Visit: `https://your-app-name.onrender.com/health`
   - Should return: `{"status":"ok"}`

4. **Test WebSocket**:
   - Visit: `https://your-app-name.onrender.com/`
   - Try logging in and connecting WebSocket

## 🔍 Troubleshooting

### Issue: Database Connection Failed
- **Solution**: Check environment variables match database credentials
- Verify `POSTGRES_HOST` includes `.onrender.com` suffix
- Check database is running in Render dashboard

### Issue: Worker Not Starting
- **Solution**: Check worker logs for errors
- Verify all environment variables are set
- Worker uses database polling (no Redis needed)

### Issue: WebSocket Not Connecting
- **Solution**: Render uses HTTPS, so WebSocket must use `wss://`
- Update WebSocket URL to use `wss://` protocol
- Check firewall/network settings

### Issue: Static Files Not Loading
- **Solution**: Verify `gateway/app/static` directory structure
- Check FastAPI static file mounting in `main.py`

## 📝 Important Notes

1. **Free Tier Limitations**:
   - Services spin down after 15 minutes of inactivity
   - First request after spin-down takes ~30 seconds
   - Consider upgrading for production use

2. **Database**:
   - Free PostgreSQL has connection limits
   - Consider connection pooling for production

3. **Redis** (Optional):
   - Not required - application works without Redis
   - If you add Redis later, it will be used automatically
   - Without Redis: Uses direct WebSocket and database polling

4. **Environment Variables**:
   - Never commit `.env` file to Git
   - Use Render's environment variable settings

## 🚀 Post-Deployment

1. **Update CORS** (if needed):
   - In `main.py`, update `allow_origins` to include your frontend domain

2. **Set up Custom Domain** (optional):
   - In Render dashboard → Settings → Custom Domain
   - Add your domain and configure DNS

3. **Monitor Logs**:
   - Regularly check logs for errors
   - Set up alerts if needed

## 📞 Support

- Render Docs: https://render.com/docs
- Render Status: https://status.render.com
- Render Community: https://community.render.com

---

**Your app should now be live at**: `https://your-app-name.onrender.com` 🎉

