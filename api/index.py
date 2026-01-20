"""
Vercel Serverless Function Entry Point
======================================
Lightweight API for Vercel deployment (no CSV data)

For full functionality with 1.7M records and ML:
- Deploy using Docker or Cloud VM (Railway, Render, AWS)
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI(
    title="Pulse of Bharat API",
    description="Governance Intelligence API - Vercel Edition (Demo)",
    version="2.0.0-vercel"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Pulse of Bharat - Governance Intelligence API",
        "version": "2.0.0-vercel",
        "status": "online",
        "note": "This is the Vercel demo. For full ML capabilities with 1.7M records, deploy on Railway/Render."
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "platform": "vercel",
        "data_loaded": False,
        "ml_ready": False,
        "note": "Vercel demo mode - CSV data not loaded due to serverless limits"
    }

@app.get("/api/stats/overview")
async def stats_overview():
    return {
        "message": "Demo Mode - Full data not available on Vercel",
        "full_system_stats": {
            "total_pincodes": 18821,
            "total_records": 1721930,
            "total_districts": 1045,
            "total_states": 55,
            "sector_alerts": {
                "education": 15554,
                "hunger": 55,
                "rural": 838,
                "electoral": 1655,
                "labor": 236
            },
            "ml_stats": {
                "total_anomalies": 1830,
                "clusters": 8
            }
        },
        "note": "These are cached stats. For live data, deploy backend on Railway/Render.",
        "github": "https://github.com/Donkon215/uidai",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/demo")
async def demo_info():
    return {
        "system": "Pulse of Bharat - Governance Intelligence",
        "capabilities": [
            "1.7M Aadhaar records analysis",
            "18,821 pincodes coverage",
            "5 governance sectors (Education, Hunger, Rural, Electoral, Labor)",
            "ML-powered anomaly detection (1,830 anomalies identified)",
            "Time series forecasting (12-month predictions)",
            "8 risk clusters via K-Means",
            "Real-time governance alerts"
        ],
        "tech_stack": [
            "FastAPI + Uvicorn",
            "Scikit-learn (IsolationForest, KMeans)",
            "Pandas + NumPy",
            "React Frontend"
        ],
        "deployment_options": {
            "vercel": "Demo mode (current)",
            "railway": "Full backend with data",
            "docker": "Complete containerized deployment",
            "cloud_vm": "Production-grade with monitoring"
        },
        "api_key": "ak_29f3no4ZE7AX1TU1O43ww4Lf5223N",
        "github": "https://github.com/Donkon215/uidai"
    }

# Vercel handler
handler = app

