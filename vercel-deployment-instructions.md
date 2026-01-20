# 🚀 Deploy to Vercel - Quick Guide

## Prerequisites
Your code is now on GitHub: https://github.com/Donkon215/uidai

## Option 1: Vercel Dashboard (Easiest - 2 minutes)

1. **Go to Vercel**: https://vercel.com/
2. **Sign in** with GitHub
3. **Click "Add New Project"**
4. **Import** your repository: `Donkon215/uidai`
5. **Configure Project:**
   - Framework Preset: `Other`
   - Root Directory: `./`
   - Build Command: (leave empty)
   - Output Directory: (leave empty)

6. **Add Environment Variables:**
   ```
   ENVIRONMENT=production
   API_KEY=ak_29f3no4ZE7AX1TU1O43ww4Lf5223N
   API_KEY_ENABLED=True
   SECRET_KEY=your-secret-key-here
   CORS_ORIGINS=["*"]
   ```

7. **Click Deploy**

## Option 2: Vercel CLI (3 minutes)

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy from local directory
cd D:\uidai_hackathon-main
vercel --prod

# Set environment variables
vercel env add ENVIRONMENT production
vercel env add API_KEY ak_29f3no4ZE7AX1TU1O43ww4Lf5223N
vercel env add API_KEY_ENABLED True
```

## ⚠️ Important Notes

### CSV Data Files
The large CSV files (1.7M records) are on GitHub but may cause issues on Vercel's serverless platform due to:
- **Memory limits**: Vercel has 1GB memory limit for serverless functions
- **Execution time**: 10-second timeout for hobby plan
- **Cold start**: Loading 1.7M records takes 5-7 seconds

### Solutions:

**Option A: Use Smaller Dataset (Recommended for Vercel)**
- Keep only `governance_intelligence_master_part01.csv` (430K records)
- Update `csv_utils.py` to load 1 chunk instead of 4
- This will work within Vercel limits

**Option B: Use External Database (Production)**
- Move CSV data to PostgreSQL/MongoDB
- Use Vercel's database integration
- Update backend to query database instead of CSV

**Option C: Deploy Backend Separately**
- Deploy backend on Railway/Render (better for data-heavy apps)
- Deploy frontend on Vercel
- Update frontend to point to backend URL

## 🎯 Recommended Deployment Strategy

For hackathon demo:

1. **Backend**: Deploy on **Railway** or **Render**
   - Better for data processing
   - Can handle 1.7M records
   - No serverless limits
   
2. **Frontend**: Deploy on **Vercel**
   - Fast global CDN
   - Perfect for React apps
   - Free tier available

### Railway Deployment (Backend)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
cd D:\uidai_hackathon-main\backend
railway init
railway up
```

### Vercel Deployment (Frontend)
```bash
cd D:\uidai_hackathon-main\frontend
vercel --prod
```

## 📝 Post-Deployment Checklist

- [ ] Backend API is accessible
- [ ] Health endpoint works: `/health`
- [ ] API key authentication working
- [ ] Frontend loads successfully
- [ ] Frontend can connect to backend
- [ ] Test key endpoints with API key

## 🔧 Troubleshooting

### Vercel: Function Timeout
- Reduce dataset size
- Or use Railway/Render for backend

### Vercel: Memory Limit
- Load only 1 CSV chunk instead of 4
- Or use external database

### CORS Errors
- Add your Vercel URL to `CORS_ORIGINS` in `.env`

## 🎉 Your Repository

**GitHub**: https://github.com/Donkon215/uidai
**Status**: ✅ Pushed successfully
**Files**: 122 objects (excluding large CSV files from tracking)

Ready to deploy! 🚀
