# Pulse of Bharat - Backend System

## Governance Intelligence API

Production-ready FastAPI backend providing REST APIs for the Pulse of Bharat National Security & Welfare Dashboard.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKEND SYSTEM                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │  DATA LAYER  │───▶│  API LAYER   │───▶│   CLIENTS    │              │
│  │  (CSV/Pandas)│    │  (FastAPI)   │    │  (React/Any) │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         │                    │                                          │
│         ▼                    ▼                                          │
│  ┌──────────────┐    ┌──────────────┐                                  │
│  │ • Merging    │    │ • REST APIs  │                                  │
│  │ • KNN Spatial│    │ • GeoJSON    │                                  │
│  │ • Anomaly    │    │ • Reports    │                                  │
│  │ • Metrics    │    │ • Statistics │                                  │
│  └──────────────┘    └──────────────┘                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Sector-Specific Metrics

### 1. Education Sector
**Metric: `School_Dropout_Risk_Index`**
- Identifies "Ghost Children" zones where enrollment exists but biometric activity is absent
- Components: Children enrolled, biometric verification, migration factors

### 2. Civil Supplies & Ration (PDS)
**Metric: `Migrant_Hunger_Score`**
- Predicts real-time food grain demand in urban slums
- Components: Adult migration, mass movement alerts, spike detection

### 3. Rural Development
**Metric: `Village_Hollow_Out_Rate`**
- Detects villages losing population for budget reallocation
- Components: Address changes, new residents, ghost population risk

### 4. Election Commission
**Metric: `Electoral_Discrepancy_Index`**
- Pre-verification layer for ERO Net
- Components: Adult enrollments, spatial anomalies, temporal spikes

### 5. Labor & Employment
**Metric: `Skill_Gap_Migration_Flow`**
- Triggers skill training programs at destination states
- Components: Labor activity, migration patterns, mass movement

---

## 🔌 API Reference

### Base URL: `http://localhost:8000`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API Health Check |
| `/api/metrics/all` | GET | All pincode metrics for map visualization |
| `/api/metrics/sector/{sector}` | GET | Sector-filtered data (education, hunger, rural, electoral, labor) |
| `/api/metrics/pincode/{pincode}` | GET | Detailed metrics for specific pincode with timeseries |
| `/api/anomalies/top-rank` | GET | Top 20 high-risk pincodes for Red Flag table |
| `/api/report/{pincode}` | GET | Generate official governance report |
| `/api/stats/overview` | GET | Dashboard statistics summary |
| `/api/stats/by-state` | GET | State-wise risk aggregation |
| `/api/map/geojson` | GET | GeoJSON formatted data for map rendering |

### Query Parameters

**`/api/metrics/sector/{sector}`**
- `min_risk` (float): Minimum risk score filter (default: 0)
- `limit` (int): Limit results (default: 100)

**`/api/anomalies/top-rank`**
- `limit` (int): Number of results (default: 20)
- `anomaly_type` (str): Filter by type (Ghost Population, Illegal Influx, Mass Migration, Sudden Spike)

**`/api/map/geojson`**
- `sector` (str): Sector to color by (education, hunger, rural, electoral, labor, all)

---

## 🗂️ Data Files Required

```
project_root/
├── chunked_data/
│   ├── governance_intelligence_master_part01.csv
│   ├── governance_intelligence_master_part02.csv
│   └── ...
├── governance_pincode_summary.csv
├── governance_alerts.csv
└── high_risk_pincodes.csv
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip packages: pandas, numpy, fastapi, uvicorn, pydantic

### Installation

```bash
# 1. Install dependencies
pip install pandas numpy fastapi uvicorn pydantic

# 2. Run the data processing pipeline first (from project root)
python phase1_data_engineering.py
python phase2_temporal_anomaly.py
python governance_metrics.py

# 3. Start API server
cd backend
python main.py
```

### Server Information
- **API URL**: http://localhost:8000
- **Interactive Docs (Swagger)**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🔧 Configuration

### CORS Settings
The API is configured to accept requests from all origins for development:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Data Path Configuration
Update `BASE_DIR` in `main.py` to match your project location:

```python
BASE_DIR = Path(r"path/to/your/project")
```

---

## 📤 Response Formats

### Metrics Response
```json
{
  "total_records": 1500,
  "data": [
    {
      "pincode": 110001,
      "state": "Delhi",
      "district": "Central Delhi",
      "latitude": 28.6139,
      "longitude": 77.2090,
      "Governance_Risk_Score": 65.5,
      "School_Dropout_Risk_Index": 45.2,
      "Migrant_Hunger_Score": 72.1,
      ...
    }
  ]
}
```

### Report Response
```json
{
  "pincode": 110001,
  "district": "Central Delhi",
  "state": "Delhi",
  "report_date": "2026-01-20 10:30:00",
  "summary": "OFFICIAL GOVERNANCE ALERT REPORT...",
  "risk_level": "HIGH",
  "recommended_actions": [
    "Deploy field verification team",
    "Cross-verify with multiple databases"
  ],
  "sector_breakdown": {
    "education": 45.2,
    "hunger": 72.1,
    "rural": 30.5,
    "electoral": 55.8,
    "labor": 40.2
  }
}
```

---

## 🔗 Government Stack Integrations

### SIR (Social Registry Information)
- Cross-validate household claims using Aadhaar biometric patterns
- Detect "Ghost Beneficiary" fraud in welfare schemes

### ERO Net (Election Commission)
- Pre-verification layer for Electoral Registration Officer network
- Flag areas with suspicious enrollment patterns

### e-Gram Swaraj
- Help Panchayats make data-driven budget decisions
- Generate budget reallocation recommendations based on population dynamics

---

## 🎯 Key Technologies

- **FastAPI**: Modern, fast web framework for building APIs
- **Pandas**: Data manipulation and analysis
- **NumPy**: Numerical computing
- **Pydantic**: Data validation using Python type annotations
- **Uvicorn**: Lightning-fast ASGI server

---

## 👥 Team

**Pulse of Bharat** - UIDAI Hackathon 2026

## 📜 License

This project is developed for the UIDAI Hackathon. All data used is synthetic/anonymized.
