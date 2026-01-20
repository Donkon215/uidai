# 🇮🇳 Pulse of Bharat - Governance Intelligence System

[![Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-black)](https://vercel.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**AI-Powered Governance Risk Analysis Platform for India**

Pulse of Bharat analyzes 1.7M+ Aadhaar records across 18,821 pincodes to identify governance vulnerabilities in 5 critical sectors using machine learning.

---

## 🎯 Overview

A production-grade governance intelligence system that leverages derivative intelligence from Aadhaar demographic data to detect risks in:
- 📚 **Education** - School-age cohort vulnerability analysis
- 🍽️ **Hunger/PDS** - Food security risk assessment  
- 🏘️ **Rural Development** - Infrastructure and services gaps
- 🗳️ **Electoral** - Voter demographic anomalies
- 👷 **Labor** - Working-age population patterns

### Key Features
- ✅ **1.7M Records Analyzed** - Real governance data processing
- ✅ **Machine Learning** - Anomaly detection + clustering + forecasting
- ✅ **21 REST APIs** - Complete programmatic access
- ✅ **Production-Ready** - Docker, Vercel, Cloud deployment
- ✅ **Real-time Analytics** - Live risk scoring and alerts
- ✅ **API Security** - Key-based authentication + rate limiting

---

## 🚀 Quick Start

### Local Development
```bash
# Clone repository
git clone https://github.com/Donkon215/uidai.git
cd uidai

# Setup environment
cd backend
cp .env.example .env
# Edit .env with your configuration

# Install dependencies
pip install -r ../requirements.txt

# Run server
cd ..
python run_server.py
```

Server runs at: http://127.0.0.1:8000
- API Docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

### Vercel Deployment
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod
```

**Note:** Due to serverless limitations, Vercel deployment runs with:
- ML models disabled (ML_ENABLED=False)
- Reduced dataset for faster cold starts
- Full functionality requires Docker/VM deployment

### Docker Deployment
```bash
docker build -t pulse-of-bharat .
docker run -p 8000:8000 --env-file backend/.env pulse-of-bharat
```

---

## 📊 System Stats

- **Data**: 1,721,930 governance records
- **Coverage**: 18,821 pincodes, 1,045 districts, 55 states
- **Alerts**: 18,338 active governance alerts
- **Anomalies**: 1,830 ML-detected patterns (9.72%)
- **Sectors**: 5 governance domains analyzed
- **Models**: Isolation Forest, K-Means, ARIMA

---

## 🔑 API Usage

### Authentication
```bash
curl -H "X-API-Key: your_api_key_here" \
     https://your-app.vercel.app/api/stats/overview
```

### Key Endpoints
- `GET /health` - System health check
- `GET /api/stats/overview` - System statistics
- `GET /api/report/{pincode}` - Pincode risk report
- `GET /api/district/{district}` - District summary
- `GET /api/ml/anomalies` - Detected anomalies
- `GET /api/forecast/{pincode}` - Time series forecast

Full API documentation: `/docs` endpoint (development mode)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│           Frontend (React)                  │
│  Interactive Dashboard + Map Visualization  │
└──────────────────┬──────────────────────────┘
                   │ REST API
┌──────────────────▼──────────────────────────┐
│         FastAPI Backend                     │
│  • 21 REST Endpoints                        │
│  • API Key Authentication                   │
│  • Rate Limiting                            │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│       ML Intelligence Engine                │
│  • Isolation Forest (Anomaly Detection)     │
│  • K-Means (Risk Clustering)                │
│  • ARIMA (Time Series Forecasting)          │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│        Data Layer (1.7M Records)            │
│  • Aadhaar Demographics                     │
│  • Governance Metrics                       │
│  • Risk Scores                              │
└─────────────────────────────────────────────┘
```

---

## 📖 Documentation

- **[README.md](README.md)** - Complete project documentation
- **[architecture.md](architecture.md)** - System architecture (15+ diagrams)
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Multi-platform deployment guide
- **[VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md)** - Vercel-specific guide
- **[FINAL_VERIFICATION_REPORT.md](FINAL_VERIFICATION_REPORT.md)** - System verification
- **[HACKATHON_DEMO_GUIDE.md](HACKATHON_DEMO_GUIDE.md)** - Demo script

---

## 🔧 Configuration

Key environment variables (see `.env.example`):

```env
# Core
ENVIRONMENT=production
API_KEY=your_secure_api_key
SECRET_KEY=generate_with_openssl_rand_hex_32

# Features
ML_ENABLED=True          # Set False for Vercel
RATE_LIMIT_ENABLED=True
CACHE_ENABLED=True

# CORS (JSON array format)
CORS_ORIGINS=["https://yourdomain.vercel.app"]
```

---

## 🧪 Testing

```bash
# Run test suite
python test_api.py

# Manual testing
curl http://localhost:8000/health
curl -H "X-API-Key: your_key" http://localhost:8000/api/stats/overview
```

---

## 🛠️ Tech Stack

**Backend:**
- FastAPI 0.104.1 (Python web framework)
- Pandas 2.1.3 (Data processing)
- Scikit-learn 1.3.2 (Machine learning)
- Pydantic 2.5.0 (Data validation)

**Deployment:**
- Vercel (Serverless functions)
- Docker (Containerization)
- Uvicorn (ASGI server)

**Frontend:**
- React 18.2.0
- Recharts 2.5.0
- Axios 1.4.0

---

## 📈 Performance

- **Response Time**: < 100ms (cached endpoints)
- **Data Loading**: ~7 seconds (1.7M records)
- **ML Processing**: < 1 second (anomaly detection)
- **Scalability**: Tested with 1.7M records, scales to 10M+

---

## 🚨 Important Notes

### Vercel Limitations
- **ML Models**: Disabled due to cold start time
- **Dataset**: Reduced/cached version for faster response
- **Memory**: 3GB max per function
- **Duration**: 60s max execution time

For full ML capabilities and complete dataset, deploy using:
- Docker (recommended for production)
- Cloud VM (AWS EC2, GCP Compute, Azure VM)
- Kubernetes cluster

---

## 🤝 Contributing

This is a hackathon project. For production use:
1. Set up external database (PostgreSQL recommended)
2. Configure Redis for caching
3. Enable full ML pipeline
4. Set up monitoring (Sentry, DataDog)
5. Configure CI/CD pipeline

---

## 📄 License

MIT License - See LICENSE file for details

---

## 👥 Team

Pulse of Bharat Development Team

---

## 🙏 Acknowledgments

- UIDAI for Aadhaar data model
- FastAPI framework team
- Scikit-learn contributors

---

## 📞 Support

- Documentation: See `/docs` files in repository
- Issues: GitHub Issues
- API Status: `/health` endpoint

---

**Built with ❤️ for better governance in India** 🇮🇳
