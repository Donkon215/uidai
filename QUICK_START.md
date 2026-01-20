# 🚀 Quick Start Guide - Production Deployment
# ============================================

**Pulse of Bharat v2.0 - Production-Ready System**

---

## ⚡ 5-Minute Production Deployment

### Option 1: Docker (Recommended) 🐳

```bash
# Step 1: Configure environment
cd uidai_hackathon-main
cp backend/.env.example backend/.env

# Step 2: Edit production values (IMPORTANT!)
# Windows: notepad backend\.env
# Linux/Mac: nano backend/.env
# Change these at minimum:
#   - SECRET_KEY (generate new: openssl rand -hex 32)
#   - ENVIRONMENT=production
#   - CORS_ORIGINS=<your-domain>

# Step 3: Build and deploy
docker-compose up -d

# Step 4: Verify deployment
curl http://localhost:8000/health
curl http://localhost:8000/

# Step 5: View logs
docker-compose logs -f backend
```

**Done! System is running at http://localhost:8000** ✅

---

### Option 2: Direct Python (Development) 🐍

```bash
# Step 1: Setup backend
cd backend
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Step 2: Install dependencies
pip install -r requirements.txt

# Step 3: Run server
python main.py

# OR with uvicorn:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Backend running at http://localhost:8000** ✅

```bash
# Step 4: Setup frontend (new terminal)
cd frontend
npm install
npm start
```

**Frontend running at http://localhost:3000** ✅

---

## 🔍 Verify Deployment

### Check System Health
```bash
# Basic health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","timestamp":"2026-01-20T..."}

# System metrics
curl http://localhost:8000/metrics

# Full system info
curl http://localhost:8000/
```

### Test Key Endpoints
```bash
# Stats overview
curl http://localhost:8000/api/stats/overview

# Get pincode report (example: 110001)
curl http://localhost:8000/api/report/110001

# Map data
curl http://localhost:8000/api/map/geojson?sector=all

# Intelligence status
curl http://localhost:8000/api/intelligence/status
```

---

## ⚙️ Essential Configuration

### Minimum Production Settings

Edit `backend/.env`:

```env
# CRITICAL - Change these!
SECRET_KEY=<generate-new-key-with-openssl-rand-hex-32>
ENVIRONMENT=production
DEBUG=False

# IMPORTANT - Configure for your domain
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com

# Recommended
RATE_LIMIT_ENABLED=True
ML_ENABLED=True
LOG_LEVEL=INFO
WORKERS=4
```

### Generate Secure Secret Key
```bash
# Linux/Mac/Git Bash:
openssl rand -hex 32

# PowerShell:
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})

# Python:
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 📊 Monitoring Dashboard

### Real-time Monitoring
```bash
# Watch health status (updates every 2 seconds)
watch -n 2 'curl -s http://localhost:8000/health | jq'

# Monitor logs continuously
# Docker:
docker-compose logs -f backend

# Python:
tail -f logs/app.log
```

### Check System Resources
```bash
# Docker stats
docker stats pulseofbharat-backend

# System processes
ps aux | grep uvicorn
ps aux | grep python

# Network connections
netstat -tuln | grep 8000
```

---

## 🐛 Troubleshooting

### Issue: Port already in use
```bash
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac:
lsof -i :8000
kill -9 <PID>

# Or change port in .env:
PORT=8080
```

### Issue: Data not loading
```bash
# Check data files exist
ls -la chunked_data/
find chunked_data/ -name "*.csv" | wc -l

# Should show 4 governance_intelligence_master files
# If missing, data pipeline needs to run first
```

### Issue: Import errors
```bash
# Reinstall dependencies
pip install --upgrade -r backend/requirements.txt

# Check Python version (must be 3.10+)
python --version

# Verify imports
python -c "import fastapi, pandas, sklearn; print('OK')"
```

### Issue: High memory usage
```bash
# Reduce workers in .env
WORKERS=2

# Disable ML if not needed
ML_ENABLED=False

# Enable caching
CACHE_ENABLED=True
CACHE_TTL=600
```

---

## 🔐 Security Checklist

Before production:
- [ ] Changed SECRET_KEY from default
- [ ] Set ENVIRONMENT=production
- [ ] Configured CORS_ORIGINS (removed *)
- [ ] Enabled RATE_LIMIT_ENABLED=True
- [ ] Set DEBUG=False
- [ ] HTTPS/SSL configured
- [ ] Firewall rules configured
- [ ] Regular backups scheduled

---

## 📈 Performance Tuning

### Optimize for your workload

```env
# High traffic (many concurrent users)
WORKERS=8
CACHE_ENABLED=True
CACHE_TTL=300
RATE_LIMIT_REQUESTS=200

# Low memory (limited RAM)
WORKERS=2
CACHE_ENABLED=False
ML_ENABLED=False

# Balanced (recommended)
WORKERS=4
CACHE_ENABLED=True
CACHE_TTL=300
ML_ENABLED=True
```

---

## 🔄 Updating the System

### Pull latest changes
```bash
# Stop services
docker-compose down
# OR
sudo systemctl stop pulseofbharat-backend

# Backup current data
tar -czf backup-$(date +%Y%m%d).tar.gz chunked_data/ logs/ .env

# Update code
git pull

# Rebuild and restart
docker-compose build
docker-compose up -d
# OR
pip install -r backend/requirements.txt
sudo systemctl restart pulseofbharat-backend

# Verify
curl http://localhost:8000/health
```

---

## 📞 Getting Help

### Check logs first
```bash
# Docker
docker-compose logs backend --tail=100

# Systemd
sudo journalctl -u pulseofbharat-backend -n 100

# Direct
tail -n 100 logs/app.log
```

### Common log locations
- Docker: `docker-compose logs`
- Systemd: `/var/log/syslog` or `journalctl`
- Direct: `logs/app.log`

### Debug mode (development only)
```env
DEBUG=True
LOG_LEVEL=DEBUG
```

---

## 🎯 Next Steps

### After successful deployment:

1. **Monitor for 24 hours**
   - Watch `/health` endpoint
   - Check error logs
   - Monitor system resources

2. **Run load tests**
   ```bash
   # Install Apache Bench
   # Windows: Download from Apache
   # Linux: apt install apache2-utils
   
   # Test endpoint
   ab -n 1000 -c 10 http://localhost:8000/api/stats/overview
   ```

3. **Set up external monitoring**
   - Uptime monitoring (UptimeRobot, Pingdom)
   - Log aggregation (ELK Stack, Splunk)
   - Metrics (Prometheus + Grafana)

4. **Configure backups**
   ```bash
   # Add to cron (daily backup)
   0 2 * * * tar -czf /backups/pulse-$(date +\%Y\%m\%d).tar.gz /app/chunked_data /app/logs
   ```

5. **Review production checklist**
   - See `PRODUCTION_CHECKLIST.md`
   - Complete all items
   - Get sign-offs

---

## 📚 Additional Resources

- **Full deployment guide**: `DEPLOYMENT.md`
- **Production checklist**: `PRODUCTION_CHECKLIST.md`
- **System architecture**: `architecture.md`
- **API documentation**: http://localhost:8000/docs
- **Project README**: `README.md`

---

## ✅ Success Indicators

Your system is production-ready when:

- ✅ Health endpoint returns "healthy"
- ✅ All API endpoints responding < 100ms
- ✅ No errors in logs (except expected ones)
- ✅ CPU usage < 60%
- ✅ Memory usage < 80%
- ✅ Data loaded successfully (1.7M+ records)
- ✅ ML models working (anomaly detection, clustering)
- ✅ Monitoring active and collecting metrics

---

**🎉 You're all set! Your Pulse of Bharat system is now production-ready.**

For issues or questions, check:
1. Logs (`docker-compose logs` or `logs/app.log`)
2. Health endpoint (`/health`)
3. System metrics (`/metrics`)
4. Troubleshooting section above
5. Full documentation in repository

---

**Version**: 2.0.0  
**Status**: Production Ready ✅  
**Last Updated**: January 20, 2026

*Pulse of Bharat - From Reactive Governance to Predictive Intelligence*
