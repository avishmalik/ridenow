# 🚀 Step-by-Step: Deploy RideNow to Render.com

## 📋 Prerequisites Checklist

- [ ] GitHub account
- [ ] Render.com account (sign up at https://render.com - free tier available)
- [ ] Code pushed to GitHub repository

---

## 🎯 Method 1: Using Render Blueprint (Recommended - Easiest)

This method uses the `render.yaml` file to automatically create all services.

### Step 1: Push Code to GitHub

```bash
# Make sure all files are committed
git add .
git commit -m "Ready for Render deployment"
git push origin main  # or your default branch
```

### Step 2: Create Blueprint on Render

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Click "New +"** button (top right)
3. **Select "Blueprint"**
4. **Connect your GitHub account** (if not already connected)
5. **Select your repository**: `ridenow` (or your repo name)
6. **Click "Apply"**

Render will automatically:
- ✅ Create PostgreSQL database (`ridenow-db`)
- ✅ Create Web Service (`ridenow-backend`)
- ✅ Create Background Worker (`ridenow-worker`)
- ✅ Link all services together
- ✅ Set up environment variables

### Step 3: Wait for Deployment

1. **Monitor the build process** in Render dashboard
2. **Check logs** for any errors
3. **Wait for "Live" status** (usually 3-5 minutes)

### Step 4: Verify Deployment

1. **Get your app URL**: `https://ridenow-backend.onrender.com` (or your custom name)
2. **Test health endpoint**: Visit `https://your-app.onrender.com/health`
   - Should return: `{"status":"ok"}`
3. **Test homepage**: Visit `https://your-app.onrender.com/`
   - Should show the login page

---

## 🛠️ Method 2: Manual Deployment (Step-by-Step)

If you prefer to create services manually or the Blueprint doesn't work:

### Step 1: Push Code to GitHub

```bash
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

### Step 2: Create PostgreSQL Database

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"PostgreSQL"**
3. Fill in:
   - **Name**: `ridenow-db`
   - **Database**: `ridenow`
   - **User**: `ridenow_user`
   - **Region**: Choose closest (e.g., `Oregon (US West)`)
   - **PostgreSQL Version**: `16` (or latest)
   - **Plan**: `Free`
4. Click **"Create Database"**
5. **Wait for database to be ready** (green status)
6. **Note down the connection details** (you'll see them in the dashboard)

### Step 3: Create Web Service (Backend)

1. In Render Dashboard, click **"New +"** → **"Web Service"**
2. **Connect GitHub** (if not already connected)
3. **Select your repository**: `ridenow`
4. Configure the service:
   - **Name**: `ridenow-backend`
   - **Region**: Same as database
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: Leave empty
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn gateway.app.main:app --host 0.0.0.0 --port $PORT`
5. **Add Environment Variables**:
   - Click **"Advanced"** → **"Add Environment Variable"**
   - Add these one by one:
   
   ```
   DATABASE_URL = <Click "Link Database" and select ridenow-db>
   ```
   
   Then manually add:
   ```
   POSTGRES_HOST = <from database dashboard>
   POSTGRES_PORT = 5432
   POSTGRES_USER = <from database dashboard>
   POSTGRES_PASSWORD = <from database dashboard>
   POSTGRES_DB = ridenow
   SECRET_KEY = <generate random string - use: openssl rand -hex 32>
   ALGORITHM = HS256
   ACCESS_TOKEN_EXPIRE_MINUTES = 30
   REDIS_HOST = (leave empty)
   REDIS_PORT = (leave empty)
   ```
6. **Link Database**:
   - Scroll down to **"Link Database"**
   - Select `ridenow-db`
   - This automatically sets `DATABASE_URL`
7. Click **"Create Web Service"**

### Step 4: Create Background Worker

1. In Render Dashboard, click **"New +"** → **"Background Worker"**
2. **Select the same repository**: `ridenow`
3. Configure:
   - **Name**: `ridenow-worker`
   - **Region**: Same as web service
   - **Branch**: `main`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python worker/ride_worker.py`
4. **Add Environment Variables** (same as web service):
   ```
   DATABASE_URL = <Link to ridenow-db>
   POSTGRES_HOST = <same as web service>
   POSTGRES_PORT = 5432
   POSTGRES_USER = <same as web service>
   POSTGRES_PASSWORD = <same as web service>
   POSTGRES_DB = ridenow
   REDIS_HOST = (leave empty)
   REDIS_PORT = (leave empty)
   ```
5. **Link Database**: Select `ridenow-db`
6. Click **"Create Background Worker"**

### Step 5: Wait for Deployment

1. **Monitor both services** in the dashboard
2. **Check logs** for errors:
   - Web Service → Logs tab
   - Worker → Logs tab
3. **Look for success messages**:
   - Web: `Database tables created successfully`
   - Worker: `Worker started, listening for ride requests...`

---

## ✅ Post-Deployment Verification

### 1. Test Health Endpoint

Visit: `https://your-app-name.onrender.com/health`

Expected response:
```json
{"status":"ok"}
```

### 2. Test Homepage

Visit: `https://your-app-name.onrender.com/`

Should show the login page.

### 3. Test API Endpoints

```bash
# Signup
curl -X POST https://your-app.onrender.com/signup \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@test.com","password":"test123","is_driver":false}'

# Login
curl -X POST https://your-app.onrender.com/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}'
```

### 4. Check Logs

**Web Service Logs** should show:
- ✅ `[Database] Using PostgreSQL at ...`
- ✅ `Database tables created successfully`
- ✅ `Application startup complete`

**Worker Logs** should show:
- ✅ `Worker started, listening for ride requests...`
- ✅ `Connected to database`

---

## 🔧 Troubleshooting

### Issue: Build Fails

**Solution**:
- Check `requirements.txt` is correct
- Verify Python version in `runtime.txt` is `python-3.11.0`
- Check build logs for specific error

### Issue: Database Connection Error

**Solution**:
- Verify `DATABASE_URL` is set (should be auto-set when linking database)
- Check `POSTGRES_*` environment variables match database credentials
- Ensure database is running (green status in dashboard)

### Issue: Worker Not Starting

**Solution**:
- Check worker logs for errors
- Verify all environment variables are set
- Ensure database is linked to worker service

### Issue: WebSocket Not Connecting

**Solution**:
- Render uses HTTPS, so WebSocket must use `wss://`
- The code already handles this automatically
- Check browser console for WebSocket errors

### Issue: 502 Bad Gateway

**Solution**:
- Service might be spinning up (free tier spins down after 15 min inactivity)
- Wait 30-60 seconds and try again
- Check service logs for errors

---

## 📝 Important Notes

### Free Tier Limitations

1. **Spin-down**: Services sleep after 15 minutes of inactivity
2. **Cold start**: First request after spin-down takes ~30 seconds
3. **Database**: Free PostgreSQL has connection limits
4. **Build time**: Free tier has slower builds

### Environment Variables

- **Never commit `.env` file** to Git
- Use Render's environment variable settings
- `DATABASE_URL` is automatically set when linking database

### Redis (Optional)

- Application works **without Redis**
- If you want Redis later:
  1. Create Redis instance in Render
  2. Add `REDIS_HOST` and `REDIS_PORT` environment variables
  3. Application will automatically use Redis

---

## 🎉 You're Done!

Your app is now live at: `https://your-app-name.onrender.com`

### Next Steps:

1. **Test the application**:
   - Sign up a new user
   - Login
   - Create a ride request
   - Test as driver

2. **Monitor logs** regularly for any issues

3. **Set up custom domain** (optional):
   - Render Dashboard → Settings → Custom Domain
   - Add your domain and configure DNS

4. **Upgrade plan** (for production):
   - Free tier is great for testing
   - Consider paid plan for production use

---

## 📞 Need Help?

- **Render Docs**: https://render.com/docs
- **Render Status**: https://status.render.com
- **Render Community**: https://community.render.com

---

**Quick Command Reference**:

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Test health endpoint
curl https://your-app.onrender.com/health

# View logs (in Render dashboard)
# Go to: Service → Logs tab
```

