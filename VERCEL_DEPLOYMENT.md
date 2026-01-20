# Vercel Deployment Guide
# =======================

## Quick Vercel Deployment

### 1. Install Vercel CLI
```bash
npm install -g vercel
```

### 2. Login to Vercel
```bash
vercel login
```

### 3. Deploy
```bash
# From project root
vercel

# Or for production
vercel --prod
```

### 4. Configure Environment Variables

In Vercel Dashboard or via CLI:

```bash
vercel env add SECRET_KEY
# Paste: <generate-with-openssl-rand-hex-32>

vercel env add API_KEY
# Paste: ak_29f3no4ZE7AX1TU1O43ww4Lf5223N

vercel env add CORS_ORIGINS
# Paste: https://yourdomain.vercel.app,*

vercel env add ENVIRONMENT
# Paste: production

vercel env add API_KEY_ENABLED
# Paste: True
```

### 5. Redeploy with Environment Variables
```bash
vercel --prod
```

## Testing Deployment

```bash
# Get your deployment URL from Vercel
# Then test:

curl https://your-app.vercel.app/health
curl https://your-app.vercel.app/api/stats/overview

# Test with API key
curl -H "X-API-Key: ak_29f3no4ZE7AX1TU1O43ww4Lf5223N" \
  https://your-app.vercel.app/api/report/110001
```

## Important Notes

1. **Data Files**: Vercel has a 50MB limit per function. If your CSV files exceed this:
   - Use external storage (S3, Cloud Storage)
   - Or split into smaller chunks
   - Or use a database instead

2. **Cold Starts**: First request may be slow (5-10 seconds)

3. **Execution Time**: Vercel functions have 10-60 second timeout (plan dependent)

4. **Memory**: Default 1GB, configurable up to 3GB

## Vercel Configuration Files

- `vercel.json` - Deployment configuration
- `api/index.py` - Serverless function entry point
- `requirements.txt` - Python dependencies (already exists)

## Troubleshooting

### Issue: Import errors
- Ensure all dependencies in `requirements.txt`
- Check Python version compatibility

### Issue: File not found
- Verify file paths are relative to function
- Use `Path(__file__).parent` for relative paths

### Issue: Timeout
- Optimize data loading
- Use caching
- Consider edge functions for static data

## Alternative: Docker on Vercel

If serverless doesn't work due to size:

```dockerfile
# Use vercel.json with Docker
{
  "builds": [
    {
      "src": "Dockerfile",
      "use": "@vercel/static-build"
    }
  ]
}
```

## Recommended: Separate Frontend/Backend

For best performance:
1. Deploy frontend to Vercel (Next.js/React)
2. Deploy backend to:
   - Railway.app (recommended)
   - Render.com
   - Fly.io
   - DigitalOcean App Platform

Then configure CORS in backend to allow Vercel frontend domain.
