"""
FastAPI Backend - Governance Intelligence API
==============================================
Production-ready REST API for the Pulse of Bharat Dashboard
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import sys

# Add parent directory to path for csv_utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from csv_utils import load_chunked_csv

# ============================================================
# APP CONFIGURATION
# ============================================================

app = FastAPI(
    title="Pulse of Bharat - Governance Intelligence API",
    description="""
    National Security & Welfare Dashboard API
    
    Provides real-time governance intelligence metrics across 5 sectors:
    - Education (School Dropout Risk)
    - Civil Supplies (Migrant Hunger Score)  
    - Rural Development (Village Hollow-Out Rate)
    - Election Commission (Electoral Discrepancy Index)
    - Labor & Employment (Skill Gap Migration Flow)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# DATA LOADING
# ============================================================

BASE_DIR = Path(__file__).parent.parent

print("Loading governance intelligence data...")

# Main datasets
try:
    governance_master = load_chunked_csv("governance_intelligence_master", low_memory=False)
    governance_master['date'] = pd.to_datetime(governance_master['date'])
    print(f"Loaded governance_master: {len(governance_master):,} records")
except Exception as e:
    print(f"Error loading governance_master: {e}")
    governance_master = pd.DataFrame()

try:
    pincode_summary = pd.read_csv(BASE_DIR / "governance_pincode_summary.csv", low_memory=False)
    print(f"Loaded pincode_summary: {len(pincode_summary):,} records")
except Exception as e:
    print(f"Error loading pincode_summary: {e}")
    pincode_summary = pd.DataFrame()

try:
    alerts_df = pd.read_csv(BASE_DIR / "governance_alerts.csv", low_memory=False)
    alerts_df['date'] = pd.to_datetime(alerts_df['date'])
    print(f"Loaded alerts: {len(alerts_df):,} records")
except Exception as e:
    print(f"Error loading alerts: {e}")
    alerts_df = pd.DataFrame()

try:
    high_risk_df = pd.read_csv(BASE_DIR / "high_risk_pincodes.csv", low_memory=False)
    high_risk_df['date'] = pd.to_datetime(high_risk_df['date'])
    print(f"Loaded high_risk: {len(high_risk_df):,} records")
except Exception as e:
    print(f"Error loading high_risk: {e}")
    high_risk_df = pd.DataFrame()

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def convert_to_json_serializable(df):
    """Convert DataFrame to JSON-serializable format."""
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == 'datetime64[ns]':
            df[col] = df[col].dt.strftime('%Y-%m-%d')
        elif df[col].dtype == 'float64':
            df[col] = df[col].replace([np.inf, -np.inf], 0).fillna(0).round(2)
    return df.to_dict(orient='records')

def get_anomaly_type(row):
    """Determine the primary anomaly type for a record."""
    if row.get('Risk_Ghost_Population', 0) == 1:
        return "Ghost Population"
    elif row.get('Risk_Influx', 0) == 1:
        return "Illegal Influx"
    elif row.get('Mass_Migration_Alert', 0) == 1:
        return "Mass Migration"
    elif row.get('Sudden_Spike_Anomaly', 0) == 1:
        return "Sudden Spike"
    else:
        return "General Risk"

# ============================================================
# API ENDPOINTS
# ============================================================

@app.get("/")
async def root():
    """API Health Check"""
    return {
        "status": "operational",
        "service": "Pulse of Bharat - Governance Intelligence API",
        "version": "1.0.0",
        "data_loaded": {
            "governance_records": len(governance_master),
            "pincodes": len(pincode_summary),
            "alerts": len(alerts_df)
        }
    }

@app.get("/api/metrics/all")
async def get_all_metrics(
    limit: Optional[int] = Query(None, description="Limit number of results")
):
    """Get all pincode metrics for map visualization."""
    if pincode_summary.empty:
        return JSONResponse(content={"total_records": 0, "data": []})
    
    df = pincode_summary.copy()
    if limit:
        df = df.head(limit)
    
    return JSONResponse(content={
        "total_records": len(df),
        "data": convert_to_json_serializable(df)
    })

@app.get("/api/metrics/sector/{sector_name}")
async def get_sector_metrics(
    sector_name: str,
    min_risk: Optional[float] = Query(0, description="Minimum risk score filter"),
    limit: Optional[int] = Query(100, description="Limit results")
):
    """Get filtered metrics for a specific sector."""
    sector_mapping = {
        "education": "School_Dropout_Risk_Index",
        "ration": "Migrant_Hunger_Score",
        "hunger": "Migrant_Hunger_Score",
        "rural": "Village_Hollow_Out_Rate",
        "electoral": "Electoral_Discrepancy_Index",
        "voting": "Electoral_Discrepancy_Index",
        "labor": "Skill_Gap_Migration_Flow",
        "employment": "Skill_Gap_Migration_Flow"
    }
    
    sector_key = sector_name.lower()
    if sector_key not in sector_mapping:
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown sector. Available: {list(sector_mapping.keys())}"
        )
    
    if pincode_summary.empty:
        return JSONResponse(content={"sector": sector_name, "total_records": 0, "data": []})
    
    metric_col = sector_mapping[sector_key]
    df = pincode_summary[pincode_summary[metric_col] >= min_risk].copy()
    df = df.nlargest(limit, metric_col)
    
    return JSONResponse(content={
        "sector": sector_name,
        "metric_column": metric_col,
        "total_records": len(df),
        "data": convert_to_json_serializable(df)
    })

@app.get("/api/metrics/pincode/{pincode}")
async def get_pincode_details(pincode: int):
    """Get detailed metrics for a specific pincode."""
    if pincode_summary.empty:
        raise HTTPException(status_code=404, detail=f"No data available")
    
    df = pincode_summary[pincode_summary['pincode'] == pincode]
    
    if df.empty:
        raise HTTPException(status_code=404, detail=f"Pincode {pincode} not found")
    
    record = df.iloc[0].to_dict()
    
    # Get time-series data for this pincode
    if not governance_master.empty:
        timeseries = governance_master[governance_master['pincode'] == pincode].copy()
        timeseries = timeseries.sort_values('date')
        ts_data = convert_to_json_serializable(timeseries.tail(30))
    else:
        ts_data = []
    
    return JSONResponse(content={
        "summary": {k: (v if not pd.isna(v) else 0) for k, v in record.items()},
        "timeseries": ts_data
    })

@app.get("/api/anomalies/top-rank")
async def get_top_anomalies(
    limit: Optional[int] = Query(20, description="Number of results"),
    anomaly_type: Optional[str] = Query(None, description="Filter by anomaly type")
):
    """Get top ranked anomalous pincodes for the Red Flag table."""
    if high_risk_df.empty:
        return JSONResponse(content={"total_alerts": 0, "data": []})
    
    df = high_risk_df.copy()
    df['anomaly_type'] = df.apply(get_anomaly_type, axis=1)
    
    if anomaly_type:
        df = df[df['anomaly_type'].str.lower().str.contains(anomaly_type.lower())]
    
    df = df.nlargest(limit, 'Risk_Score')
    
    output_cols = ['date', 'pincode', 'state', 'district', 'anomaly_type', 'Risk_Score',
                   'total_demographic', 'total_enrolment', 'Risk_Category']
    available_cols = [c for c in output_cols if c in df.columns]
    df = df[available_cols].copy()
    
    return JSONResponse(content={
        "total_alerts": len(df),
        "data": convert_to_json_serializable(df)
    })

@app.get("/api/report/{pincode}")
async def generate_report(pincode: int):
    """Generate an official text report for a specific pincode."""
    if pincode_summary.empty:
        raise HTTPException(status_code=404, detail="No data available")
    
    summary = pincode_summary[pincode_summary['pincode'] == pincode]
    
    if summary.empty:
        raise HTTPException(status_code=404, detail=f"Pincode {pincode} not found")
    
    record = summary.iloc[0]
    
    gov_score = record.get('Governance_Risk_Score', 0)
    if gov_score >= 70:
        risk_level = "CRITICAL"
    elif gov_score >= 50:
        risk_level = "HIGH"
    elif gov_score >= 30:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    primary_concern = record.get('Primary_Sector_Concern', 'General')
    
    action_mapping = {
        'Education': [
            "Deploy Anganwadi inspection team",
            "Cross-verify school enrollment records",
            "Initiate door-to-door child survey"
        ],
        'Rural_Hollowing': [
            "Review MGNREGA fund allocation",
            "Assess elderly care infrastructure",
            "Evaluate local employment opportunities"
        ],
        'Labor': [
            "Coordinate with e-Shram registration centers",
            "Deploy mobile labor registration units",
            "Initiate skill development programs"
        ],
        'Electoral': [
            "Alert Electoral Registration Officer (ERO)",
            "Cross-verify with Voter ID database",
            "Initiate address verification drive"
        ],
        'Ration/Hunger': [
            "Increase PDS shop grain allocation",
            "Deploy mobile ration units",
            "Activate emergency food distribution"
        ]
    }
    
    actions = action_mapping.get(primary_concern, [
        "Deploy field verification team",
        "Cross-verify with multiple databases",
        "Initiate detailed audit"
    ])
    
    summary_text = f"""
OFFICIAL GOVERNANCE ALERT REPORT
================================
Report ID: GOV-{pincode}-{datetime.now().strftime('%Y%m%d%H%M')}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

LOCATION DETAILS:
- Pincode: {pincode}
- District: {record.get('district', 'N/A')}
- State: {record.get('state', 'N/A')}

RISK ASSESSMENT: {risk_level}
- Governance Risk Score: {gov_score:.1f}/100
- Primary Concern: {primary_concern}

RECOMMENDED ACTIONS:
{chr(10).join(f'  {i+1}. {action}' for i, action in enumerate(actions))}

---
Auto-generated by Pulse of Bharat Governance Intelligence System
"""
    
    return JSONResponse(content={
        "pincode": pincode,
        "district": record.get('district', 'N/A'),
        "state": record.get('state', 'N/A'),
        "report_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "summary": summary_text,
        "risk_level": risk_level,
        "recommended_actions": actions,
        "sector_breakdown": {
            "education": round(record.get('School_Dropout_Risk_Index', 0), 2),
            "hunger": round(record.get('Migrant_Hunger_Score', 0), 2),
            "rural": round(record.get('Village_Hollow_Out_Rate', 0), 2),
            "electoral": round(record.get('Electoral_Discrepancy_Index', 0), 2),
            "labor": round(record.get('Skill_Gap_Migration_Flow', 0), 2)
        }
    })

@app.get("/api/stats/overview")
async def get_overview_stats():
    """Get overall dashboard statistics."""
    if pincode_summary.empty:
        return JSONResponse(content={"total_pincodes": 0, "error": "No data loaded"})
    
    return JSONResponse(content={
        "total_pincodes": len(pincode_summary),
        "total_records": len(governance_master) if not governance_master.empty else 0,
        "risk_distribution": {
            "critical": int((pincode_summary['Governance_Risk_Score'] >= 70).sum()),
            "high": int(((pincode_summary['Governance_Risk_Score'] >= 50) & 
                        (pincode_summary['Governance_Risk_Score'] < 70)).sum()),
            "medium": int(((pincode_summary['Governance_Risk_Score'] >= 30) & 
                          (pincode_summary['Governance_Risk_Score'] < 50)).sum()),
            "low": int((pincode_summary['Governance_Risk_Score'] < 30).sum())
        },
        "sector_summary": {
            "education_alerts": int((pincode_summary['School_Dropout_Risk_Index'] > 70).sum()),
            "hunger_alerts": int((pincode_summary['Migrant_Hunger_Score'] > 70).sum()),
            "rural_alerts": int((pincode_summary['Village_Hollow_Out_Rate'] > 70).sum()),
            "electoral_alerts": int((pincode_summary['Electoral_Discrepancy_Index'] > 70).sum()),
            "labor_alerts": int((pincode_summary['Skill_Gap_Migration_Flow'] > 70).sum())
        }
    })

@app.get("/api/stats/by-state")
async def get_state_stats():
    """Get risk statistics aggregated by state."""
    if pincode_summary.empty:
        return JSONResponse(content={"total_states": 0, "data": []})
    
    state_stats = pincode_summary.groupby('state').agg({
        'pincode': 'count',
        'Governance_Risk_Score': 'mean',
        'School_Dropout_Risk_Index': 'mean',
        'Migrant_Hunger_Score': 'mean'
    }).reset_index()
    
    state_stats.columns = ['state', 'pincode_count', 'avg_risk', 'education', 'hunger']
    state_stats = state_stats.sort_values('avg_risk', ascending=False)
    
    return JSONResponse(content={
        "total_states": len(state_stats),
        "data": convert_to_json_serializable(state_stats)
    })

@app.get("/api/map/geojson")
async def get_map_geojson(
    sector: Optional[str] = Query("all", description="Sector to color by")
):
    """Get GeoJSON formatted data for map visualization."""
    if pincode_summary.empty:
        return JSONResponse(content={"type": "FeatureCollection", "features": []})
    
    df = pincode_summary.copy()
    
    sector_mapping = {
        "education": "School_Dropout_Risk_Index",
        "hunger": "Migrant_Hunger_Score",
        "rural": "Village_Hollow_Out_Rate",
        "electoral": "Electoral_Discrepancy_Index",
        "labor": "Skill_Gap_Migration_Flow",
        "all": "Governance_Risk_Score"
    }
    
    color_metric = sector_mapping.get(sector.lower(), "Governance_Risk_Score")
    
    features = []
    for _, row in df.iterrows():
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row['longitude']), float(row['latitude'])]
            },
            "properties": {
                "pincode": int(row['pincode']),
                "state": str(row['state']),
                "district": str(row['district']),
                "risk_score": round(float(row[color_metric]), 2),
                "governance_score": round(float(row['Governance_Risk_Score']), 2)
            }
        }
        features.append(feature)
    
    return JSONResponse(content={
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "color_metric": color_metric,
            "total_features": len(features)
        }
    })

@app.get("/api/analytics/forecasts")
async def get_forecasts():
    """Get forecasting data for predictions."""
    try:
        forecasts_df = pd.read_csv(BASE_DIR / "data" / "processed" / "forecasts.csv")
        return JSONResponse(content={
            "total_records": len(forecasts_df),
            "data": convert_to_json_serializable(forecasts_df)
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e), "data": []})

@app.get("/api/analytics/state-risk")
async def get_state_risk():
    """Get state-wise risk summary for heatmap."""
    try:
        state_df = pd.read_csv(BASE_DIR / "data" / "processed" / "state_risk_summary.csv")
        return JSONResponse(content={
            "total_states": len(state_df),
            "data": convert_to_json_serializable(state_df)
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e), "data": []})

@app.get("/api/analytics/clusters")
async def get_clusters():
    """Get cluster analysis data."""
    try:
        cluster_df = pd.read_csv(BASE_DIR / "data" / "processed" / "cluster_analysis.csv")
        return JSONResponse(content={
            "total_clusters": len(cluster_df),
            "data": convert_to_json_serializable(cluster_df)
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e), "data": []})

@app.get("/api/analytics/government-insights")
async def get_government_insights():
    """Get ministry-wise government insights."""
    try:
        insights_df = pd.read_csv(BASE_DIR / "data" / "processed" / "government_insights.csv")
        return JSONResponse(content={
            "total_ministries": len(insights_df),
            "data": convert_to_json_serializable(insights_df)
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e), "data": []})

@app.get("/api/map/district-aggregation")
async def get_district_aggregation(
    sector: Optional[str] = Query("all", description="Sector to aggregate by")
):
    """Get district-level aggregated data for choropleth map."""
    if pincode_summary.empty:
        return JSONResponse(content={"data": []})
    
    sector_mapping = {
        "education": "School_Dropout_Risk_Index",
        "hunger": "Migrant_Hunger_Score",
        "rural": "Village_Hollow_Out_Rate",
        "electoral": "Electoral_Discrepancy_Index",
        "labor": "Skill_Gap_Migration_Flow",
        "all": "Governance_Risk_Score"
    }
    
    metric = sector_mapping.get(sector.lower(), "Governance_Risk_Score")
    
    # Aggregate by district
    district_agg = pincode_summary.groupby(['state', 'district']).agg({
        'pincode': 'count',
        'latitude': 'mean',
        'longitude': 'mean',
        'Governance_Risk_Score': 'mean',
        'School_Dropout_Risk_Index': 'mean',
        'Migrant_Hunger_Score': 'mean',
        'Village_Hollow_Out_Rate': 'mean',
        'Electoral_Discrepancy_Index': 'mean',
        'Skill_Gap_Migration_Flow': 'mean'
    }).reset_index()
    
    district_agg.columns = ['state', 'district', 'pincode_count', 'latitude', 'longitude',
                            'governance', 'education', 'hunger', 'rural', 'electoral', 'labor']
    
    district_agg['risk_score'] = district_agg[metric.lower().replace('_risk_index', '').replace('_score', '').replace('_out_rate', '').replace('_discrepancy_index', '').replace('_gap_migration_flow', '') if sector != 'all' else 'governance']
    
    # Fix risk_score mapping
    if sector == 'education':
        district_agg['risk_score'] = district_agg['education']
    elif sector == 'hunger':
        district_agg['risk_score'] = district_agg['hunger']
    elif sector == 'rural':
        district_agg['risk_score'] = district_agg['rural']
    elif sector == 'electoral':
        district_agg['risk_score'] = district_agg['electoral']
    elif sector == 'labor':
        district_agg['risk_score'] = district_agg['labor']
    else:
        district_agg['risk_score'] = district_agg['governance']
    
    return JSONResponse(content={
        "total_districts": len(district_agg),
        "sector": sector,
        "data": convert_to_json_serializable(district_agg)
    })

@app.get("/api/map/state-aggregation")
async def get_state_aggregation():
    """Get state-level aggregated data for choropleth map."""
    if pincode_summary.empty:
        return JSONResponse(content={"data": []})
    
    # Aggregate by state
    state_agg = pincode_summary.groupby('state').agg({
        'pincode': 'count',
        'latitude': 'mean',
        'longitude': 'mean',
        'Governance_Risk_Score': 'mean',
        'School_Dropout_Risk_Index': 'mean',
        'Migrant_Hunger_Score': 'mean',
        'Village_Hollow_Out_Rate': 'mean',
        'Electoral_Discrepancy_Index': 'mean',
        'Skill_Gap_Migration_Flow': 'mean'
    }).reset_index()
    
    state_agg.columns = ['state', 'pincode_count', 'latitude', 'longitude',
                         'governance', 'education', 'hunger', 'rural', 'electoral', 'labor']
    
    return JSONResponse(content={
        "total_states": len(state_agg),
        "data": convert_to_json_serializable(state_agg)
    })

# India boundary coordinates for filtering
INDIA_BOUNDS = {
    "min_lat": 6.5,
    "max_lat": 35.5,
    "min_lng": 68.0,
    "max_lng": 97.5
}

@app.get("/api/map/filtered-pincodes")
async def get_filtered_pincodes(
    sector: Optional[str] = Query("all", description="Sector to filter by")
):
    """Get pincodes filtered within India boundaries."""
    if pincode_summary.empty:
        return JSONResponse(content={"data": []})
    
    # Filter to India bounds
    df = pincode_summary[
        (pincode_summary['latitude'] >= INDIA_BOUNDS['min_lat']) &
        (pincode_summary['latitude'] <= INDIA_BOUNDS['max_lat']) &
        (pincode_summary['longitude'] >= INDIA_BOUNDS['min_lng']) &
        (pincode_summary['longitude'] <= INDIA_BOUNDS['max_lng'])
    ].copy()
    
    return JSONResponse(content={
        "total_records": len(df),
        "bounds": INDIA_BOUNDS,
        "data": convert_to_json_serializable(df)
    })

# ============================================================
# GOVERNANCE INTELLIGENCE ENGINE INTEGRATION
# ============================================================

# Initialize governance intelligence engine
try:
    from governance_intelligence_engine import (
        GovernanceIntelligenceEngine, 
        LLMResponseGenerator,
        MODEL_VERSION
    )
    from llm_chat_service import LLMChatService, OfflineLLMService, UserRole
    
    gi_engine = GovernanceIntelligenceEngine()
    llm_response_gen = LLMResponseGenerator()
    offline_llm = OfflineLLMService()
    
    # Prepare district-level data for the engine
    if not governance_master.empty:
        # Determine which columns exist for aggregation
        agg_dict = {'pincode': 'count'}
        
        # Age columns from the data
        age_cols = {
            'age_0_5': 'sum',
            'age_5_17': 'sum', 
            'age_18_greater': 'sum',
            'demo_age_5_17': 'sum',
            'demo_age_17_': 'sum',
            'bio_age_5_17': 'sum',
            'bio_age_17_': 'sum',
            'children_enrolled': 'sum',
            'adult_migration_volume': 'sum',
            'labor_activity': 'sum'
        }
        
        for col, agg_func in age_cols.items():
            if col in governance_master.columns:
                agg_dict[col] = agg_func
        
        # Create district-aggregated data
        district_data = governance_master.groupby(['state', 'district']).agg(agg_dict).reset_index()
        
        # Map to engine expected columns
        # age_0_5 -> already present
        # age_5_17 -> already present
        # age_17_plus -> use age_18_greater if present
        if 'age_18_greater' in district_data.columns:
            district_data['age_17_plus'] = district_data['age_18_greater']
        elif 'demo_age_17_' in district_data.columns:
            district_data['age_17_plus'] = district_data['demo_age_17_']
        else:
            district_data['age_17_plus'] = 0
            
        # Calculate new_registrations as sum of demographic activities
        reg_cols = [c for c in ['demo_age_5_17', 'demo_age_17_', 'bio_age_5_17', 'bio_age_17_'] if c in district_data.columns]
        if reg_cols:
            district_data['new_registrations'] = district_data[reg_cols].sum(axis=1)
        elif 'children_enrolled' in district_data.columns:
            district_data['new_registrations'] = district_data['children_enrolled']
        else:
            district_data['new_registrations'] = 0
            
        district_data['year'] = 2026
        print(f"Governance Intelligence Engine initialized with {len(district_data)} districts")
        print(f"  Available columns: {list(district_data.columns)}")
    else:
        district_data = pd.DataFrame()
        print("Warning: No data for Governance Intelligence Engine")
    
    GI_ENGINE_AVAILABLE = True
except Exception as e:
    print(f"Governance Intelligence Engine not available: {e}")
    GI_ENGINE_AVAILABLE = False
    district_data = pd.DataFrame()

# Pydantic models for requests
class ChatRequest(BaseModel):
    message: str
    role: str = "district_admin"
    district: Optional[str] = None
    conversation_history: Optional[List[dict]] = None

class ForecastRequest(BaseModel):
    district: str
    horizons: Optional[List[int]] = [1, 5, 10]

@app.get("/api/intelligence/status")
async def get_intelligence_status():
    """Check if the Governance Intelligence Engine is available."""
    return JSONResponse(content={
        "engine_available": GI_ENGINE_AVAILABLE,
        "model_version": MODEL_VERSION if GI_ENGINE_AVAILABLE else "N/A",
        "districts_loaded": len(district_data) if not district_data.empty else 0,
        "features": {
            "forecasting": GI_ENGINE_AVAILABLE,
            "policy_mapping": GI_ENGINE_AVAILABLE,
            "chatbot": GI_ENGINE_AVAILABLE,
            "data_quality": GI_ENGINE_AVAILABLE
        }
    })

@app.get("/api/intelligence/roles")
async def get_available_roles():
    """Get list of available chatbot roles."""
    return JSONResponse(content={
        "roles": [
            {"id": "police", "label": "Police Administration", "icon": "👮"},
            {"id": "district_admin", "label": "District Administration", "icon": "🏛️"},
            {"id": "state_govt", "label": "State Government", "icon": "🏢"},
            {"id": "budget", "label": "Budget & Finance", "icon": "💰"},
            {"id": "education", "label": "Education Department", "icon": "🎓"},
            {"id": "health", "label": "Health Department", "icon": "🏥"},
            {"id": "skill", "label": "Skill & Employment", "icon": "🛠️"}
        ]
    })

@app.post("/api/intelligence/forecast")
async def generate_forecast(request: ForecastRequest):
    """Generate demographic forecast for a district."""
    if not GI_ENGINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Intelligence Engine not available")
    
    if district_data.empty:
        raise HTTPException(status_code=404, detail="No district data available")
    
    district = request.district
    
    # Check if district exists
    if district not in district_data['district'].values:
        # Try fuzzy match
        matches = district_data[district_data['district'].str.contains(district, case=False, na=False)]
        if matches.empty:
            raise HTTPException(status_code=404, detail=f"District '{district}' not found")
        district = matches.iloc[0]['district']
    
    try:
        result = gi_engine.process_district(district_data, district, request.horizons)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/intelligence/forecast-matrix")
async def get_forecast_matrix(
    limit: Optional[int] = Query(20, description="Number of districts to include")
):
    """Get the forecast matrix for multiple districts."""
    if not GI_ENGINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Intelligence Engine not available")
    
    if district_data.empty:
        return JSONResponse(content={"data": [], "columns": []})
    
    try:
        districts = district_data['district'].unique()[:limit]
        matrix_df = gi_engine.get_forecast_matrix(district_data, districts.tolist())
        
        return JSONResponse(content={
            "total_districts": len(districts),
            "model_version": MODEL_VERSION,
            "columns": list(matrix_df.columns),
            "data": convert_to_json_serializable(matrix_df)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/intelligence/district/{district_name}")
async def get_district_intelligence(district_name: str):
    """Get full governance intelligence for a specific district."""
    if not GI_ENGINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Intelligence Engine not available")
    
    if district_data.empty:
        raise HTTPException(status_code=404, detail="No district data available")
    
    # Find district
    matches = district_data[district_data['district'].str.contains(district_name, case=False, na=False)]
    if matches.empty:
        raise HTTPException(status_code=404, detail=f"District '{district_name}' not found")
    
    district = matches.iloc[0]['district']
    
    try:
        result = gi_engine.process_district(district_data, district)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/intelligence/chat")
async def chat_with_intelligence(request: ChatRequest):
    """Chat with the governance intelligence system."""
    if not GI_ENGINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Intelligence Engine not available")
    
    # Map role string to enum
    role_mapping = {
        "police": UserRole.POLICE,
        "district_admin": UserRole.DISTRICT_ADMIN,
        "state_govt": UserRole.STATE_GOVT,
        "budget": UserRole.BUDGET_FINANCE,
        "education": UserRole.EDUCATION,
        "health": UserRole.HEALTH,
        "skill": UserRole.SKILL_EMPLOYMENT
    }
    
    role = role_mapping.get(request.role.lower(), UserRole.DISTRICT_ADMIN)
    
    # Get district context
    district = request.district
    if district and not district_data.empty:
        matches = district_data[district_data['district'].str.contains(district, case=False, na=False)]
        if not matches.empty:
            district = matches.iloc[0]['district']
            # Generate intelligence for this district
            result = gi_engine.process_district(district_data, district)
            context = llm_response_gen.generate_context(result, role.value)
        else:
            context = {"district": district, "data_quality": "unknown", "model_version": MODEL_VERSION}
    else:
        # Use first available district for demo
        if not district_data.empty:
            district = district_data.iloc[0]['district']
            result = gi_engine.process_district(district_data, district)
            context = llm_response_gen.generate_context(result, role.value)
        else:
            context = {"error": "No district data available"}
    
    # Generate response using offline service (always available)
    response = offline_llm.generate_response(context, role, request.message)
    
    return JSONResponse(content={
        "success": True,
        "answer": response,
        "role": role.value,
        "district": district,
        "model_version": MODEL_VERSION,
        "context_used": True
    })

@app.get("/api/intelligence/sample-questions")
async def get_sample_questions(
    role: Optional[str] = Query("district_admin", description="User role")
):
    """Get sample questions for a specific role."""
    samples = {
        "police": [
            "What is the projected youth population growth?",
            "Which areas need additional police personnel?",
            "What is the law and order stress level?",
            "How does migration affect policing needs?"
        ],
        "education": [
            "How many additional school seats are needed?",
            "What is the dropout risk in this district?",
            "What is the education budget stress level?",
            "When should we plan for new schools?"
        ],
        "health": [
            "What is the hospital bed demand projection?",
            "How many additional doctors are needed?",
            "What is the maternity load trend?",
            "Which health facilities need expansion?"
        ],
        "budget": [
            "What is the overall budget stress level?",
            "Which sectors need priority funding?",
            "What is the education budget index change?",
            "How should we reallocate resources?"
        ],
        "district_admin": [
            "What is the overall district projection?",
            "Which departments need coordination?",
            "What are the priority action items?",
            "What is the infrastructure stress timeline?"
        ],
        "state_govt": [
            "Compare this district with peers",
            "What is the state-wide trend?",
            "Which districts need intervention?",
            "What policy changes are recommended?"
        ],
        "skill": [
            "What is the skill training demand?",
            "How does migration affect skill availability?",
            "How many training centers are needed?",
            "What skills are in demand?"
        ]
    }
    
    return JSONResponse(content={
        "role": role,
        "questions": samples.get(role.lower(), samples["district_admin"])
    })

@app.get("/api/intelligence/districts")
async def get_available_districts():
    """Get list of available districts for the chatbot."""
    if district_data.empty:
        return JSONResponse(content={"districts": []})
    
    districts = district_data[['state', 'district']].drop_duplicates().to_dict('records')
    
    # Group by state
    by_state = {}
    for d in districts:
        state = d['state']
        if state not in by_state:
            by_state[state] = []
        by_state[state].append(d['district'])
    
    return JSONResponse(content={
        "total_districts": len(districts),
        "by_state": by_state
    })

# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
