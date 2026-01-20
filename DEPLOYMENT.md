# Production Deployment Guide
# ============================

## Pulse of Bharat - Production Deployment

This guide covers deploying Pulse of Bharat to production environments.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Deployment Methods](#deployment-methods)
4. [Configuration](#configuration)
5. [Monitoring & Maintenance](#monitoring--maintenance)
6. [Scaling](#scaling)
7. [Security](#security)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 20GB minimum for data and logs
- **OS**: Linux (Ubuntu 20.04+ or RHEL 8+), Windows Server 2019+

### Software Requirements

- Python 3.10+
- Node.js 18+ (for frontend)
- Docker & Docker Compose (optional)
- Nginx or Apache (for reverse proxy)

---

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd uidai_hackathon-main
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with production values
nano .env
```

### 3. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Build for production
npm run build
```

---

## Deployment Methods

### Method 1: Docker Deployment (Recommended)

#### Build and Run

```bash
# Build image
docker build -t pulseofbharat:latest .

# Run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f backend

# Check health
curl http://localhost:8000/health
```

#### Configuration

Edit `docker-compose.yml` to customize:
- Port mappings
- Environment variables
- Resource limits
- Volume mounts

### Method 2: Systemd Service (Linux)

#### Create Service File

```bash
sudo nano /etc/systemd/system/pulseofbharat-backend.service
```

```ini
[Unit]
Description=Pulse of Bharat Backend API
After=network.target

[Service]
Type=simple
User=appuser
WorkingDirectory=/opt/pulseofbharat/backend
Environment="PATH=/opt/pulseofbharat/venv/bin"
ExecStart=/opt/pulseofbharat/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable pulseofbharat-backend
sudo systemctl start pulseofbharat-backend
sudo systemctl status pulseofbharat-backend
```

### Method 3: Cloud Deployment

#### AWS EC2

```bash
# On EC2 instance
sudo apt update
sudo apt install python3.10 python3.10-venv nginx

# Setup application (follow Backend Setup above)

# Configure nginx
sudo nano /etc/nginx/sites-available/pulseofbharat
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/pulseofbharat /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### Azure App Service

```bash
# Create App Service
az webapp create --name pulseofbharat --resource-group myResourceGroup --plan myAppServicePlan --runtime "PYTHON:3.10"

# Configure environment
az webapp config appsettings set --name pulseofbharat --resource-group myResourceGroup --settings ENVIRONMENT=production

# Deploy code
az webapp up --name pulseofbharat --runtime "PYTHON:3.10"
```

#### Google Cloud Run

```bash
# Build and push container
gcloud builds submit --tag gcr.io/PROJECT_ID/pulseofbharat

# Deploy
gcloud run deploy pulseofbharat \
  --image gcr.io/PROJECT_ID/pulseofbharat \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

## Configuration

### Production .env Template

```env
# Production Configuration
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<generate-with-openssl-rand-hex-32>

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4

# CORS
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com

# Security
API_KEY_ENABLED=True
API_KEY=<your-secret-api-key>
RATE_LIMIT_ENABLED=True
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# ML
ML_ENABLED=True
ANOMALY_CONTAMINATION=0.1
N_CLUSTERS=8

# Monitoring
MONITORING_ENABLED=True
```

### Security Checklist

- [ ] Change SECRET_KEY from default
- [ ] Enable API_KEY_ENABLED if needed
- [ ] Configure CORS_ORIGINS (remove *)
- [ ] Enable HTTPS/TLS
- [ ] Set up firewall rules
- [ ] Implement IP whitelisting if needed
- [ ] Regular security updates

---

## Monitoring & Maintenance

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed metrics
curl http://localhost:8000/metrics

# Readiness check
curl http://localhost:8000/ready
```

### Log Monitoring

```bash
# View application logs
tail -f logs/app.log

# With Docker
docker-compose logs -f backend

# With systemd
sudo journalctl -u pulseofbharat-backend -f
```

### Performance Monitoring

```bash
# CPU and Memory
htop

# Network
netstat -tuln | grep 8000

# Disk usage
df -h
```

### Automated Monitoring Setup

```bash
# Install Prometheus (optional)
docker run -d -p 9090:9090 prom/prometheus

# Configure alerts
# Edit prometheus.yml to scrape /metrics endpoint
```

---

## Scaling

### Horizontal Scaling

#### Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml pulseofbharat

# Scale service
docker service scale pulseofbharat_backend=4
```

#### Kubernetes

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pulseofbharat-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pulseofbharat
  template:
    metadata:
      labels:
        app: pulseofbharat
    spec:
      containers:
      - name: backend
        image: pulseofbharat:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: WORKERS
          value: "4"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

```bash
kubectl apply -f deployment.yaml
```

### Vertical Scaling

#### Increase Workers

```env
# In .env
WORKERS=8  # Increase based on CPU cores
```

#### Resource Limits (Docker)

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
```

---

## Security

### SSL/TLS Setup

```bash
# Using Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
sudo certbot renew --dry-run
```

### Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# iptables
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -A INPUT -j DROP
```

### API Key Management

```bash
# Generate secure API key
openssl rand -hex 32

# Set in .env
API_KEY=<generated-key>
API_KEY_ENABLED=True
```

---

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check logs
docker-compose logs backend
# OR
sudo journalctl -u pulseofbharat-backend -n 100

# Check port conflicts
sudo lsof -i :8000
```

#### High Memory Usage

```bash
# Reduce workers
WORKERS=2  # In .env

# Monitor memory
watch -n 1 'free -m'
```

#### Slow API Responses

```bash
# Check metrics
curl http://localhost:8000/metrics

# Enable caching
CACHE_ENABLED=True  # In .env

# Increase cache TTL
CACHE_TTL=600  # 10 minutes
```

#### Data Not Loading

```bash
# Check data directory permissions
ls -la chunked_data/

# Verify CSV files exist
find chunked_data/ -name "*.csv" | wc -l

# Check logs for specific errors
grep "ERROR" logs/app.log
```

### Support

For issues not covered here:
1. Check logs: `logs/app.log`
2. Review configuration: `.env`
3. Test health endpoints: `/health`, `/ready`
4. Contact support with error ID from logs

---

## Backup & Recovery

### Backup Strategy

```bash
# Backup data
tar -czf backup-$(date +%Y%m%d).tar.gz chunked_data/ logs/ .env

# Backup to cloud (example)
aws s3 cp backup-$(date +%Y%m%d).tar.gz s3://your-bucket/backups/
```

### Recovery

```bash
# Restore from backup
tar -xzf backup-20260120.tar.gz

# Restart services
docker-compose restart
# OR
sudo systemctl restart pulseofbharat-backend
```

---

## Performance Tuning

### Recommended Settings

```env
# Production Optimized
WORKERS=4  # Match CPU cores
CACHE_ENABLED=True
CACHE_TTL=300
ML_ENABLED=True
RATE_LIMIT_REQUESTS=100
TIMEOUT=60
KEEP_ALIVE=5
```

### Load Testing

```bash
# Using Apache Bench
ab -n 1000 -c 10 http://localhost:8000/

# Using wrk
wrk -t4 -c100 -d30s http://localhost:8000/api/stats/overview
```

---

## Maintenance Schedule

- **Daily**: Check logs for errors
- **Weekly**: Review metrics and performance
- **Monthly**: Update dependencies, security patches
- **Quarterly**: Review and optimize configuration

---

**Deployed by**: Pulse of Bharat Team  
**Last Updated**: January 20, 2026  
**Version**: 2.0.0
