# Pulse of Bharat - Production Checklist
# ========================================

## Pre-Deployment Checklist

### Backend Configuration
- [ ] Update `.env` file with production values
- [ ] Change `SECRET_KEY` from default
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=False`
- [ ] Configure `CORS_ORIGINS` (remove *)
- [ ] Enable and configure `API_KEY` if needed
- [ ] Set appropriate `LOG_LEVEL=INFO`
- [ ] Configure `WORKERS` based on CPU cores
- [ ] Review and set `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW`
- [ ] Verify `DATA_DIR` path is correct
- [ ] Test all configuration values

### Frontend Configuration
- [ ] Set `REACT_APP_API_URL` to production backend URL
- [ ] Set `NODE_ENV=production`
- [ ] Disable `REACT_APP_DEBUG_MODE`
- [ ] Configure `REACT_APP_ENABLE_ANALYTICS` if applicable
- [ ] Build production bundle: `npm run build`
- [ ] Test production build locally
- [ ] Optimize images and assets
- [ ] Enable service worker if needed

### Security
- [ ] SSL/TLS certificate installed and configured
- [ ] HTTPS enforced on all endpoints
- [ ] Firewall configured (allow 80, 443, 22 only)
- [ ] API keys secured and rotated
- [ ] Rate limiting enabled
- [ ] Input validation enabled
- [ ] CORS properly configured
- [ ] No sensitive data in logs
- [ ] Error messages don't expose internals
- [ ] Security headers configured (HSTS, CSP, etc.)

### Data & Storage
- [ ] All CSV data files present in `chunked_data/`
- [ ] Data integrity verified
- [ ] Backup strategy implemented
- [ ] Log rotation configured
- [ ] Sufficient disk space (20GB+ free)
- [ ] Database migrations applied (if using DB)
- [ ] Data validation passing

### Performance
- [ ] Load testing completed
- [ ] Response times < 100ms for key endpoints
- [ ] Memory usage optimized
- [ ] Caching enabled and configured
- [ ] Static assets compressed
- [ ] CDN configured (if applicable)
- [ ] Database indexes created (if using DB)
- [ ] ML models loaded successfully

### Monitoring & Logging
- [ ] `/health` endpoint responding correctly
- [ ] `/metrics` endpoint accessible
- [ ] `/ready` endpoint configured
- [ ] Log aggregation set up
- [ ] Error tracking configured
- [ ] Uptime monitoring enabled
- [ ] Alert system configured
- [ ] Dashboard for metrics available
- [ ] Log retention policy set

### Testing
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] API endpoints tested manually
- [ ] Frontend routes tested
- [ ] Error scenarios tested
- [ ] Load testing completed
- [ ] Security scanning completed
- [ ] Cross-browser testing done

### Infrastructure
- [ ] Server/VM provisioned with adequate resources
- [ ] Reverse proxy (Nginx/Apache) configured
- [ ] Load balancer configured (if applicable)
- [ ] Auto-scaling configured (if applicable)
- [ ] Container orchestration ready (if using K8s/Swarm)
- [ ] DNS records configured
- [ ] Network security groups configured
- [ ] Backup systems tested

### Documentation
- [ ] README.md updated
- [ ] API documentation current
- [ ] DEPLOYMENT.md reviewed
- [ ] architecture.md verified
- [ ] presentation_ppt.md finalized
- [ ] Environment variables documented
- [ ] Troubleshooting guide available
- [ ] Runbook created

### Deployment Process
- [ ] Deployment scripts tested
- [ ] Rollback procedure documented
- [ ] Zero-downtime deployment planned
- [ ] Health checks during deployment configured
- [ ] Smoke tests post-deployment planned
- [ ] Team notified of deployment window
- [ ] Maintenance page ready (if needed)

---

## Deployment Steps

### 1. Pre-Deployment
```bash
# Backup current system
tar -czf backup-$(date +%Y%m%d).tar.gz chunked_data/ logs/ .env

# Run tests
pytest tests/
npm test

# Build frontend
cd frontend && npm run build

# Verify configuration
python backend/config.py
```

### 2. Deployment
```bash
# Using Docker
docker-compose down
docker-compose build
docker-compose up -d

# OR using systemd
sudo systemctl stop pulseofbharat-backend
git pull
pip install -r backend/requirements.txt
sudo systemctl start pulseofbharat-backend
```

### 3. Post-Deployment Verification
```bash
# Check health
curl https://yourdomain.com/health

# Check metrics
curl https://yourdomain.com/metrics

# Test key endpoints
curl https://yourdomain.com/api/stats/overview
curl https://yourdomain.com/api/map/geojson

# Check logs
tail -f logs/app.log

# Monitor for 15 minutes
watch -n 5 'curl -s https://yourdomain.com/health | jq'
```

---

## Post-Deployment

### Immediate (0-4 hours)
- [ ] Verify all endpoints responding
- [ ] Check error logs for issues
- [ ] Monitor system resources
- [ ] Verify data loading correctly
- [ ] Test user workflows
- [ ] Confirm metrics collection working

### Short-term (4-24 hours)
- [ ] Review performance metrics
- [ ] Check for any error spikes
- [ ] Verify caching working
- [ ] Monitor API response times
- [ ] Review user feedback (if any)
- [ ] Confirm backup jobs running

### Medium-term (1-7 days)
- [ ] Analyze usage patterns
- [ ] Review and optimize slow queries
- [ ] Check for memory leaks
- [ ] Verify log rotation working
- [ ] Review security logs
- [ ] Plan for any needed optimizations

---

## Rollback Procedure

If issues occur:

```bash
# Stop current deployment
docker-compose down
# OR
sudo systemctl stop pulseofbharat-backend

# Restore from backup
tar -xzf backup-YYYYMMDD.tar.gz

# Restart services
docker-compose up -d
# OR
sudo systemctl start pulseofbharat-backend

# Verify rollback successful
curl http://localhost:8000/health
```

---

## Emergency Contacts

- **Backend Lead**: [Contact Info]
- **Frontend Lead**: [Contact Info]
- **DevOps**: [Contact Info]
- **Security**: [Contact Info]

---

## Production Metrics Baseline

After 24 hours of production:

- **Average Response Time**: _______ ms
- **95th Percentile Response**: _______ ms
- **Error Rate**: _______ %
- **Uptime**: _______ %
- **CPU Usage**: _______ %
- **Memory Usage**: _______ %
- **Requests/Hour**: _______
- **Active Users**: _______

---

## Sign-Off

- [ ] Backend Team Lead: ________________ Date: ______
- [ ] Frontend Team Lead: ________________ Date: ______
- [ ] DevOps Engineer: ________________ Date: ______
- [ ] Security Officer: ________________ Date: ______
- [ ] Project Manager: ________________ Date: ______

---

**Deployment Date**: January 20, 2026  
**Version**: 2.0.0  
**Environment**: Production  
**Deployment Method**: Docker / Systemd / Cloud  

---

## Notes

(Add any deployment-specific notes here)
