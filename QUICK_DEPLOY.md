# ⚡ Quick Deploy to Render.com

## 🚀 Fastest Method (5 minutes)

### 1. Push to GitHub
```bash
git add .
git commit -m "Deploy to Render"
git push origin main
```

### 2. Deploy on Render
1. Go to: https://dashboard.render.com
2. Click **"New +"** → **"Blueprint"**
3. Connect GitHub → Select your repo
4. Click **"Apply"**
5. Wait 3-5 minutes

### 3. Done! 🎉
Your app: `https://ridenow-backend.onrender.com`

---

## 📋 What Gets Created

- ✅ PostgreSQL Database (`ridenow-db`)
- ✅ Web Service (`ridenow-backend`)
- ✅ Background Worker (`ridenow-worker`)

---

## ✅ Verify It Works

1. Visit: `https://your-app.onrender.com/health`
   - Should show: `{"status":"ok"}`

2. Visit: `https://your-app.onrender.com/`
   - Should show login page

---

## 🔧 If Something Goes Wrong

**Check Logs**:
- Render Dashboard → Your Service → Logs tab
- Look for errors in red

**Common Issues**:
- Build fails → Check `requirements.txt`
- Database error → Verify database is linked
- 502 error → Wait 30 seconds (service spinning up)

---

## 📖 Full Guide

See `DEPLOY_STEPS.md` for detailed instructions.
