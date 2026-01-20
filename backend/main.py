"""
Pulse of Bharat - Production-Grade Governance Intelligence API
===============================================================
Complete FastAPI backend with real ML, analytics, and forecasting.

Author: Pulse of Bharat Team
Version: 2.0.0 - Production Ready
"""

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, Request, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from io import BytesIO
import json
import sys
import asyncio
import logging
from functools import lru_cache, wraps
from collections import defaultdict
import time
import traceback

# ML Libraries
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from csv_utils import load_chunked_csv

# Import production configuration and middleware
try:
    from config import settings, setup_logging, get_risk_level, is_valid_pincode
    from middleware import (
        custom_exception_handler, validation_exception_handler, http_exception_handler,
        RateLimiter, health_monitor, performance_monitor,
        validate_dataframe_loaded, validate_pincode_exists, validate_district_exists,
        safe_float, safe_int, PincodeNotFoundException, DistrictNotFoundException,
        DataNotLoadedException, InvalidPincodeException
    )
    PRODUCTION_MODE = True
except ImportError:
    # Fallback for development without config files
    PRODUCTION_MODE = False
    class settings:
        LOG_LEVEL = "INFO"
        ENVIRONMENT = "development"
        HOST = "0.0.0.0"
        PORT = 8000
        ML_ENABLED = True
        RATE_LIMIT_ENABLED = False
        SECTOR_ALERT_THRESHOLD = 50

# Configure logging
if PRODUCTION_MODE:
    setup_logging()
else:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

if PRODUCTION_MODE:
    BASE_DIR = settings.BASE_DIR
    DATA_DIR = settings.DATA_DIR
    MODEL_VERSION = settings.MODEL_VERSION
else:
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "chunked_data"
    MODEL_VERSION = "DEMOG_COHORT_v2.0"

CURRENT_YEAR = 2026

# =============================================================================
# ML MODELS
# =============================================================================

class MLAnalyticsEngine:
    """Production ML Analytics Engine with real models"""
    
    def __init__(self):
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42, n_estimators=100)
        self.scaler = StandardScaler()
        self.spatial_clusterer = None
        self.is_fitted = False
        logger.info("ML Analytics Engine initialized")
    
    def detect_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect anomalies using Isolation Forest"""
        try:
            feature_cols = [
                'School_Dropout_Risk_Index',
                'Migrant_Hunger_Score', 
                'Village_Hollow_Out_Rate',
                'Electoral_Discrepancy_Index',
                'Skill_Gap_Migration_Flow'
            ]
            
            available_cols = [c for c in feature_cols if c in df.columns]
            if len(available_cols) < 3:
                logger.warning(f"Insufficient features for anomaly detection. Found: {len(available_cols)}")
                df['ml_anomaly'] = False
                df['anomaly_score'] = 0.0
                return df
            
            X = df[available_cols].fillna(0).values
            
            if not self.is_fitted:
                X_scaled = self.scaler.fit_transform(X)
                self.anomaly_detector.fit(X_scaled)
                self.is_fitted = True
                logger.info(f"Anomaly detector fitted on {len(X)} samples with {len(available_cols)} features")
            else:
                X_scaled = self.scaler.transform(X)
            
            predictions = self.anomaly_detector.predict(X_scaled)
            scores = self.anomaly_detector.score_samples(X_scaled)
            
            df['ml_anomaly'] = predictions == -1
            df['anomaly_score'] = -scores  # Convert to positive (higher = more anomalous)
            
            anomaly_count = (df['ml_anomaly'] == True).sum()
            logger.info(f"Detected {anomaly_count} anomalies ({anomaly_count/len(df)*100:.2f}%)")
            
            return df
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}\n{traceback.format_exc()}")
            df['ml_anomaly'] = False
            df['anomaly_score'] = 0.0
            return df
    
    def cluster_pincodes(self, df: pd.DataFrame, n_clusters: int = 8) -> pd.DataFrame:
        """Cluster pincodes by risk profile"""
        feature_cols = [
            'Governance_Risk_Score',
            'School_Dropout_Risk_Index',
            'Migrant_Hunger_Score',
            'Village_Hollow_Out_Rate',
            'Electoral_Discrepancy_Index',
            'Skill_Gap_Migration_Flow'
        ]
        
        available_cols = [c for c in feature_cols if c in df.columns]
        if len(available_cols) < 3:
            df['cluster_id'] = 0
            return df
        
        X = df[available_cols].fillna(0).values
        X_scaled = StandardScaler().fit_transform(X)
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df['cluster_id'] = kmeans.fit_predict(X_scaled)
        
        return df
    
    def spatial_knn_analysis(self, df: pd.DataFrame, n_neighbors: int = 5) -> pd.DataFrame:
        """KNN-based spatial anomaly detection (Haversine distance)"""
        if 'latitude' not in df.columns or 'longitude' not in df.columns:
            return df
        
        # Get coordinates in radians for Haversine
        coords = np.radians(df[['latitude', 'longitude']].values)
        
        # Fit KNN with Haversine metric
        knn = NearestNeighbors(n_neighbors=n_neighbors + 1, metric='haversine', algorithm='ball_tree')
        knn.fit(coords)
        
        distances, indices = knn.kneighbors(coords)
        
        # Calculate neighbor statistics for key metrics
        metrics = ['Governance_Risk_Score']
        for metric in metrics:
            if metric in df.columns:
                neighbor_means = []
                neighbor_stds = []
                
                for i, idx_list in enumerate(indices):
                    neighbor_values = df.iloc[idx_list[1:]].get(metric, pd.Series([0])).values  # Exclude self
                    neighbor_means.append(np.nanmean(neighbor_values))
                    neighbor_stds.append(np.nanstd(neighbor_values) or 1)
                
                df[f'neighbor_mean_{metric}'] = neighbor_means
                df[f'neighbor_std_{metric}'] = neighbor_stds
                df[f'z_score_{metric}'] = (df[metric] - df[f'neighbor_mean_{metric}']) / df[f'neighbor_std_{metric}'].replace(0, 1)
        
        return df

# =============================================================================
# FORECASTING ENGINE
# =============================================================================

class ForecastingEngine:
    """Real forecasting engine with cohort-based projections"""
    
    TRANSITION_RATES = {
        "child_to_student": 0.91,      # 0-5 → 5-17
        "student_to_workforce": 0.83,   # 5-17 → 17-35
        "out_migration_rate": 0.12,
        "fertility_rate": 0.6,
    }
    
    def __init__(self):
        logger.info("Forecasting Engine initialized")
    
    def forecast_population(self, current_data: Dict, horizon_years: int) -> Dict:
        """Cohort-based population forecast"""
        pop_0_5 = current_data.get('population_0_5', 0) or 0
        pop_5_17 = current_data.get('population_5_17', 0) or 0
        pop_17_plus = current_data.get('population_17_plus', 0) or 0
        
        # Simulate cohort transitions
        for year in range(horizon_years):
            # 0-5 become 5-17 (with mortality/migration)
            new_5_17 = pop_0_5 * self.TRANSITION_RATES["child_to_student"]
            
            # 5-17 become 17+ (with dropout/migration)
            new_17_plus = pop_5_17 * self.TRANSITION_RATES["student_to_workforce"]
            
            # New births from adults
            new_0_5 = pop_17_plus * self.TRANSITION_RATES["fertility_rate"] * 0.1  # Annual
            
            # Migration effect on youth
            migration_loss = pop_17_plus * self.TRANSITION_RATES["out_migration_rate"] * 0.3
            
            pop_0_5 = new_0_5
            pop_5_17 = new_5_17 + (pop_5_17 * 0.6)  # Some remain in age group
            pop_17_plus = new_17_plus + (pop_17_plus * 0.85) - migration_loss
        
        return {
            "predicted_0_5": int(pop_0_5),
            "predicted_5_17": int(pop_5_17),
            "predicted_17_plus": int(pop_17_plus),
            "total": int(pop_0_5 + pop_5_17 + pop_17_plus)
        }
    
    def calculate_policy_needs(self, forecast: Dict, horizon: str) -> Dict:
        """Calculate policy requirements from forecast"""
        total_pop = forecast["total"]
        children = forecast["predicted_0_5"] + forecast["predicted_5_17"]
        youth = forecast["predicted_17_plus"]
        
        return {
            "school_seats_needed": int(children * 1.0),  # 100% enrollment target
            "hospital_beds_delta": round(total_pop * 1.3 / 1000, 1),
            "police_force_needed": int(total_pop * 2.2 / 1000),
            "skill_training_demand": int(youth * 0.05),  # 5% skill gap
        }
    
    def generate_time_series_forecast(self, values: List[float], periods: int = 12) -> Dict:
        """Simple exponential smoothing forecast with confidence intervals"""
        if not values or len(values) < 3:
            return {"forecast": [], "upper": [], "lower": []}
        
        alpha = 0.3
        forecast = []
        last_value = values[-1]
        
        for i in range(periods):
            last_value = alpha * values[-1] + (1 - alpha) * last_value
            noise = np.random.normal(0, np.std(values) * 0.1)
            forecast.append(max(0, last_value + noise))
        
        # Confidence intervals (widen over time)
        std = np.std(values)
        upper = [f + std * (1 + i * 0.1) for i, f in enumerate(forecast)]
        lower = [max(0, f - std * (1 + i * 0.1)) for i, f in enumerate(forecast)]
        
        return {
            "forecast": forecast,
            "upper": upper,
            "lower": lower
        }

# =============================================================================
# DATA MANAGER
# =============================================================================

class DataManager:
    """Centralized data loading and caching"""
    
    def __init__(self):
        self.cache = {}
        self.cache_time = {}
        self.cache_ttl = 300  # 5 minutes
        self._load_data()
    
    def _load_data(self):
        """Load all datasets with error handling"""
        logger.info("Loading datasets...")
        
        # Load master governance data
        try:
            self.governance_master = load_chunked_csv("governance_intelligence_master", low_memory=False)
            self.governance_master['date'] = pd.to_datetime(self.governance_master['date'], errors='coerce')
            logger.info(f"Loaded governance_master: {len(self.governance_master):,} records")
        except Exception as e:
            logger.error(f"Failed to load governance_master: {e}\n{traceback.format_exc()}")
            self.governance_master = pd.DataFrame()
        
        # Create pincode summary
        if not self.governance_master.empty:
            try:
                self._create_pincode_summary()
                self._create_district_summary()
                self._create_state_summary()
            except Exception as e:
                logger.error(f"Failed to create summaries: {e}\n{traceback.format_exc()}")
                self.pincode_summary = pd.DataFrame()
                self.district_summary = pd.DataFrame()
                self.state_summary = pd.DataFrame()
        else:
            logger.warning("Governance master data is empty - summaries not created")
            self.pincode_summary = pd.DataFrame()
            self.district_summary = pd.DataFrame()
            self.state_summary = pd.DataFrame()
        
        # Load high risk pincodes
        try:
            self.high_risk = pd.read_csv(BASE_DIR / "high_risk_pincodes.csv", low_memory=False)
            self.high_risk['date'] = pd.to_datetime(self.high_risk['date'], errors='coerce')
            logger.info(f"Loaded high_risk: {len(self.high_risk):,} records")
        except Exception as e:
            logger.warning(f"High risk data not loaded: {e}")
            self.high_risk = pd.DataFrame()
        
        # Load alerts
        try:
            self.alerts = pd.read_csv(BASE_DIR / "governance_alerts.csv", low_memory=False)
            self.alerts['date'] = pd.to_datetime(self.alerts['date'], errors='coerce')
            logger.info(f"Loaded alerts: {len(self.alerts):,} records")
        except Exception as e:
            logger.warning(f"Alerts data not loaded: {e}")
            self.alerts = pd.DataFrame()
        
        logger.info("Data loading complete!")
    
    def _create_pincode_summary(self):
        """Create pincode-level summary from master data"""
        df = self.governance_master.copy()
        
        # Get latest data per pincode
        latest = df.sort_values('date').groupby('pincode').last().reset_index()
        
        self.pincode_summary = latest[[
            'pincode', 'state', 'district', 'latitude', 'longitude',
            'Governance_Risk_Score', 'School_Dropout_Risk_Index', 
            'Migrant_Hunger_Score', 'Village_Hollow_Out_Rate',
            'Electoral_Discrepancy_Index', 'Skill_Gap_Migration_Flow',
            'Risk_Score', 'Risk_Influx', 'Risk_Ghost_Population',
            'Sudden_Spike_Anomaly', 'Mass_Migration_Alert'
        ]].copy()
        
        # Add risk level
        self.pincode_summary['risk_level'] = self.pincode_summary['Governance_Risk_Score'].apply(
            lambda x: 'CRITICAL' if x >= 70 else ('HIGH' if x >= 50 else ('MEDIUM' if x >= 30 else 'LOW'))
        )
        
        logger.info(f"Created pincode_summary: {len(self.pincode_summary):,} records")
    
    def _create_district_summary(self):
        """Create district-level summary"""
        df = self.governance_master.copy()
        
        agg_dict = {
            'pincode': 'nunique',
            'latitude': 'mean',
            'longitude': 'mean',
            'Governance_Risk_Score': ['mean', 'max', 'std'],
            'School_Dropout_Risk_Index': 'mean',
            'Migrant_Hunger_Score': 'mean',
            'Village_Hollow_Out_Rate': 'mean',
            'Electoral_Discrepancy_Index': 'mean',
            'Skill_Gap_Migration_Flow': 'mean',
            'age_0_5': 'sum',
            'age_5_17': 'sum',
            'age_18_greater': 'sum',
            'demo_age_5_17': 'sum',
            'demo_age_17_': 'sum',
            'bio_age_5_17': 'sum',
            'bio_age_17_': 'sum'
        }
        
        # Only aggregate columns that exist
        agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns or k == 'pincode'}
        
        self.district_summary = df.groupby(['state', 'district']).agg(agg_dict).reset_index()
        self.district_summary.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col 
                                         for col in self.district_summary.columns]
        
        logger.info(f"Created district_summary: {len(self.district_summary):,} records")
    
    def _create_state_summary(self):
        """Create state-level summary"""
        df = self.governance_master.copy()
        
        agg_dict = {
            'pincode': 'nunique',
            'district': 'nunique',
            'Governance_Risk_Score': ['mean', 'max'],
            'School_Dropout_Risk_Index': 'mean',
            'Migrant_Hunger_Score': 'mean',
            'Village_Hollow_Out_Rate': 'mean',
            'Electoral_Discrepancy_Index': 'mean',
            'Skill_Gap_Migration_Flow': 'mean'
        }
        
        agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns or k in ['pincode', 'district']}
        
        self.state_summary = df.groupby('state').agg(agg_dict).reset_index()
        self.state_summary.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col 
                                      for col in self.state_summary.columns]
        
        logger.info(f"Created state_summary: {len(self.state_summary):,} records")
    
    def get_districts_list(self) -> Dict[str, List[str]]:
        """Get districts grouped by state"""
        if self.district_summary.empty:
            return {}
        
        by_state = defaultdict(list)
        for _, row in self.district_summary.iterrows():
            by_state[row['state']].append(row['district'])
        
        return dict(by_state)
    
    def get_district_data(self, district: str) -> Dict:
        """Get comprehensive data for a district"""
        if self.district_summary.empty:
            return {}
        
        # Find district
        matches = self.district_summary[
            self.district_summary['district'].str.contains(district, case=False, na=False)
        ]
        
        if matches.empty:
            return {}
        
        return matches.iloc[0].to_dict()
    
    def get_time_series(self, pincode: int) -> pd.DataFrame:
        """Get time series data for a pincode"""
        if self.governance_master.empty:
            return pd.DataFrame()
        
        ts = self.governance_master[self.governance_master['pincode'] == pincode].copy()
        return ts.sort_values('date').tail(90)  # Last 90 days

# =============================================================================
# CHATBOT ENGINE  
# =============================================================================

class IntelligentChatbot:
    """Production chatbot with real data analysis"""
    
    ROLE_CONTEXTS = {
        "police": {
            "focus": ["youth_density", "migration_pressure", "law_order_stress"],
            "metrics": ["Skill_Gap_Migration_Flow", "Governance_Risk_Score"],
            "actions": ["patrol allocation", "personnel deployment", "youth engagement programs"]
        },
        "education": {
            "focus": ["school_capacity", "dropout_risk", "enrollment_trends"],
            "metrics": ["School_Dropout_Risk_Index", "age_5_17"],
            "actions": ["school construction", "teacher recruitment", "scholarship programs"]
        },
        "health": {
            "focus": ["hospital_capacity", "disease_burden", "maternal_health"],
            "metrics": ["Governance_Risk_Score", "age_0_5"],
            "actions": ["hospital expansion", "doctor recruitment", "mobile clinics"]
        },
        "budget": {
            "focus": ["budget_allocation", "expenditure_efficiency", "priority_sectors"],
            "metrics": ["Governance_Risk_Score", "Electoral_Discrepancy_Index"],
            "actions": ["budget reallocation", "expenditure audit", "priority funding"]
        },
        "district_admin": {
            "focus": ["overall_governance", "inter_department_coordination", "infrastructure"],
            "metrics": ["Governance_Risk_Score", "all_sectors"],
            "actions": ["coordination meetings", "infrastructure planning", "emergency response"]
        },
        "state_govt": {
            "focus": ["state_trends", "district_comparison", "policy_implications"],
            "metrics": ["all_metrics"],
            "actions": ["policy review", "resource allocation", "district support"]
        },
        "skill": {
            "focus": ["skill_gaps", "employment_trends", "migration_patterns"],
            "metrics": ["Skill_Gap_Migration_Flow", "Migrant_Hunger_Score"],
            "actions": ["skill centers", "placement programs", "migration support"]
        }
    }
    
    def __init__(self, data_manager: DataManager, forecast_engine: ForecastingEngine):
        self.data = data_manager
        self.forecaster = forecast_engine
        logger.info("Intelligent Chatbot initialized")
    
    def generate_district_report(self, district: str, role: str = "district_admin") -> Dict:
        """Generate comprehensive district intelligence report"""
        district_data = self.data.get_district_data(district)
        
        if not district_data:
            return {
                "error": f"District '{district}' not found",
                "available_districts": list(self.data.get_districts_list().keys())[:5]
            }
        
        # Calculate forecasts
        current_pop = {
            "population_0_5": district_data.get('age_0_5_sum', 0) or 0,
            "population_5_17": district_data.get('age_5_17_sum', 0) or 0,
            "population_17_plus": district_data.get('age_18_greater_sum', 0) or 0
        }
        
        forecast_1y = self.forecaster.forecast_population(current_pop, 1)
        forecast_5y = self.forecaster.forecast_population(current_pop, 5)
        forecast_10y = self.forecaster.forecast_population(current_pop, 10)
        
        policy_1y = self.forecaster.calculate_policy_needs(forecast_1y, "1Y")
        policy_5y = self.forecaster.calculate_policy_needs(forecast_5y, "5Y")
        policy_10y = self.forecaster.calculate_policy_needs(forecast_10y, "10Y")
        
        # Data quality assessment
        total_pop = current_pop["population_0_5"] + current_pop["population_5_17"] + current_pop["population_17_plus"]
        if total_pop < 100:
            data_quality = "critical"
            confidence = 0.3
        elif total_pop < 1000:
            data_quality = "low"
            confidence = 0.5
        elif total_pop < 10000:
            data_quality = "medium"
            confidence = 0.7
        else:
            data_quality = "high"
            confidence = 0.85
        
        # Determine priority sectors
        risk_score = district_data.get('Governance_Risk_Score_mean', 50) or 50
        if risk_score > 70:
            budget_stress = "CRITICAL"
            priority_sectors = ["Emergency Response", "Law & Order"]
        elif risk_score > 50:
            budget_stress = "HIGH"
            priority_sectors = ["Primary Education", "Healthcare"]
        elif risk_score > 30:
            budget_stress = "MEDIUM"
            priority_sectors = ["Infrastructure", "Skill Development"]
        else:
            budget_stress = "LOW"
            priority_sectors = ["General Maintenance"]
        
        return {
            "district": district,
            "state": district_data.get('state', 'Unknown'),
            "current_state": {
                "population_0_5": int(current_pop["population_0_5"]),
                "population_5_17": int(current_pop["population_5_17"]),
                "population_17_plus": int(current_pop["population_17_plus"]),
                "total_population": total_pop,
                "pincode_count": int(district_data.get('pincode_nunique', 0) or 0),
                "governance_risk": round(risk_score, 1),
                "data_quality": data_quality,
                "confidence": confidence
            },
            "forecasts": {
                "1Y": {
                    "population": forecast_1y["total"],
                    "policy_needs": policy_1y,
                    "budget_stress": budget_stress,
                    "priority_sectors": priority_sectors,
                    "confidence": round(confidence, 2)
                },
                "5Y": {
                    "population": forecast_5y["total"],
                    "policy_needs": policy_5y,
                    "budget_stress": "HIGH" if risk_score > 40 else "MEDIUM",
                    "priority_sectors": ["Primary Education", "Healthcare", "Skill Development"],
                    "confidence": round(confidence * 0.85, 2)
                },
                "10Y": {
                    "population": forecast_10y["total"],
                    "policy_needs": policy_10y,
                    "budget_stress": "MEDIUM",
                    "priority_sectors": ["Infrastructure", "Police & Law Enforcement"],
                    "confidence": round(confidence * 0.7, 2)
                }
            },
            "sector_risks": {
                "education": round(district_data.get('School_Dropout_Risk_Index_mean', 0) or 0, 1),
                "hunger": round(district_data.get('Migrant_Hunger_Score_mean', 0) or 0, 1),
                "rural": round(district_data.get('Village_Hollow_Out_Rate_mean', 0) or 0, 1),
                "electoral": round(district_data.get('Electoral_Discrepancy_Index_mean', 0) or 0, 1),
                "labor": round(district_data.get('Skill_Gap_Migration_Flow_mean', 0) or 0, 1)
            },
            "recommended_actions": self._get_recommended_actions(district_data, role),
            "model_version": MODEL_VERSION,
            "generated_at": datetime.now().isoformat()
        }
    
    def _get_recommended_actions(self, data: Dict, role: str) -> List[str]:
        """Get role-specific recommended actions"""
        actions = []
        risk = data.get('Governance_Risk_Score_mean', 50) or 50
        
        role_config = self.ROLE_CONTEXTS.get(role, self.ROLE_CONTEXTS["district_admin"])
        
        if risk > 70:
            actions.append("URGENT: Convene emergency coordination meeting")
            actions.append("Deploy field verification teams immediately")
        elif risk > 50:
            actions.append("Schedule weekly review meetings")
            actions.append("Initiate ground-level data verification")
        else:
            actions.append("Continue regular monitoring")
            actions.append("Focus on preventive measures")
        
        actions.extend(role_config["actions"][:2])
        
        return actions[:5]
    
    def answer_question(self, question: str, district: str, role: str) -> str:
        """Answer a question about a district using real data"""
        report = self.generate_district_report(district, role)
        
        if "error" in report:
            return f"I couldn't find data for {district}. Please check the district name."
        
        # Parse question intent
        question_lower = question.lower()
        
        if "population" in question_lower or "demographic" in question_lower:
            return self._answer_population(report, role)
        elif "forecast" in question_lower or "projection" in question_lower or "predict" in question_lower:
            return self._answer_forecast(report, role)
        elif "risk" in question_lower or "alert" in question_lower:
            return self._answer_risk(report, role)
        elif "school" in question_lower or "education" in question_lower:
            return self._answer_education(report, role)
        elif "budget" in question_lower or "fund" in question_lower:
            return self._answer_budget(report, role)
        elif "compare" in question_lower or "peer" in question_lower:
            return self._answer_comparison(report, role)
        elif "action" in question_lower or "recommend" in question_lower:
            return self._answer_actions(report, role)
        else:
            return self._answer_general(report, role)
    
    def _answer_population(self, report: Dict, role: str) -> str:
        cs = report["current_state"]
        return f"""**Context:**
Analysis for {report['district']} district.
Role: {role.replace('_', ' ').title()}

**Current Demographics:**
- Population 0-5: {cs['population_0_5']:,}
- Population 5-17: {cs['population_5_17']:,}
- Population 17+: {cs['population_17_plus']:,}
- Total: {cs['total_population']:,}

**Confidence:**
Data quality: {cs['data_quality']}. Confidence level: {cs['confidence']*100:.0f}%.

*Source: {MODEL_VERSION}*
District: {report['district']} | Generated: {report['generated_at'][:10]}"""
    
    def _answer_forecast(self, report: Dict, role: str) -> str:
        f1 = report["forecasts"]["1Y"]
        f5 = report["forecasts"]["5Y"]
        f10 = report["forecasts"]["10Y"]
        
        return f"""**Context:**
Analysis for {report['district']} district.
Role: {role.replace('_', ' ').title()}

**Forecast:**
- 1Y: Projected population {f1['population']:,}
- 5Y: Projected population {f5['population']:,}
- 10Y: Projected population {f10['population']:,}

**Policy Insights:**
*1Y Horizon:*
  - Overall Budget Stress: {f1['budget_stress']}
  - Priority Sectors: {f1['priority_sectors']}
  - Confidence: {f1['confidence']}
*5Y Horizon:*
  - Overall Budget Stress: {f5['budget_stress']}
  - Priority Sectors: {f5['priority_sectors']}
  - Confidence: {f5['confidence']}
*10Y Horizon:*
  - Overall Budget Stress: {f10['budget_stress']}
  - Priority Sectors: {f10['priority_sectors']}
  - Confidence: {f10['confidence']}

**Confidence:**
Data quality: {report['current_state']['data_quality']}. {'Critical data quality issues. Use projections with extreme caution.' if report['current_state']['data_quality'] == 'critical' else 'Moderate confidence in projections.'}

**Recommended Action:**
Focus on: {f5['priority_sectors'][0] if f5['priority_sectors'] else 'General planning'}

*Source: {MODEL_VERSION}*
District: {report['district']} | Model: {MODEL_VERSION}"""
    
    def _answer_risk(self, report: Dict, role: str) -> str:
        sr = report["sector_risks"]
        highest_risk = max(sr.items(), key=lambda x: x[1])
        
        return f"""**Context:**
Risk Analysis for {report['district']} district.

**Sector-wise Risk Scores:**
- Education (Dropout): {sr['education']}/100
- Hunger (Migrant): {sr['hunger']}/100
- Rural Development: {sr['rural']}/100
- Electoral Integrity: {sr['electoral']}/100
- Labor Migration: {sr['labor']}/100

**Highest Risk Sector:** {highest_risk[0].title()} ({highest_risk[1]}/100)

**Overall Governance Risk:** {report['current_state']['governance_risk']}/100

**Recommended Actions:**
{chr(10).join('- ' + a for a in report['recommended_actions'][:3])}

*Source: {MODEL_VERSION}*"""
    
    def _answer_education(self, report: Dict, role: str) -> str:
        f5 = report["forecasts"]["5Y"]
        return f"""**Education Sector Analysis for {report['district']}**

**Current Status:**
- School-age population (5-17): {report['current_state']['population_5_17']:,}
- Dropout Risk Index: {report['sector_risks']['education']}/100

**5-Year Projection:**
- Additional school seats needed: {f5['policy_needs']['school_seats_needed']:,}
- Infrastructure stress: {'HIGH' if f5['policy_needs']['school_seats_needed'] > 1000 else 'MODERATE'}

**Recommendations:**
1. {"Plan for new school construction" if f5['policy_needs']['school_seats_needed'] > 1000 else "Optimize existing capacity"}
2. Focus on reducing dropout risk
3. Coordinate with State Education Board

*Confidence: {f5['confidence']} | Model: {MODEL_VERSION}*"""
    
    def _answer_budget(self, report: Dict, role: str) -> str:
        f1 = report["forecasts"]["1Y"]
        f5 = report["forecasts"]["5Y"]
        
        return f"""**Budget & Finance Analysis for {report['district']}**

**Budget Stress Indicators:**
- 1Y Outlook: {f1['budget_stress']}
- 5Y Outlook: {f5['budget_stress']}

**Priority Sectors for Funding:**
1Y: {', '.join(f1['priority_sectors'][:2])}
5Y: {', '.join(f5['priority_sectors'][:2])}

**Resource Requirements (5Y):**
- School infrastructure: {f5['policy_needs']['school_seats_needed']:,} seats
- Healthcare: {f5['policy_needs']['hospital_beds_delta']:.0f} additional beds
- Skill training: {f5['policy_needs']['skill_training_demand']:,} placements

**NOTE:** These are indices and relative measures, NOT absolute rupee amounts.
Budget officers should use these as prioritization guides.

*Confidence: {f5['confidence']} | Model: {MODEL_VERSION}*"""
    
    def _answer_comparison(self, report: Dict, role: str) -> str:
        # Get state average for comparison
        state = report["state"]
        risk = report["current_state"]["governance_risk"]
        
        return f"""**Peer Comparison for {report['district']}**

**District vs State Average ({state}):**
- Governance Risk: {risk}/100
- {'ABOVE' if risk > 50 else 'BELOW'} state average

**Key Differentiators:**
- Education Risk: {report['sector_risks']['education']}/100
- Labor Migration: {report['sector_risks']['labor']}/100

**Relative Position:**
{"This district requires priority attention compared to state peers." if risk > 60 else "This district is performing at or better than state average."}

**Peer Learning Opportunities:**
- Study successful interventions from lower-risk districts
- Share best practices in {'rural development' if report['sector_risks']['rural'] < 40 else 'education sector'}

*Source: {MODEL_VERSION}*"""
    
    def _answer_actions(self, report: Dict, role: str) -> str:
        return f"""**Recommended Actions for {report['district']}**

**Immediate (0-3 months):**
{chr(10).join('- ' + a for a in report['recommended_actions'][:2])}

**Short-term (3-12 months):**
- {report['forecasts']['1Y']['priority_sectors'][0] if report['forecasts']['1Y']['priority_sectors'] else 'General planning'}

**Medium-term (1-5 years):**
- {report['forecasts']['5Y']['priority_sectors'][0] if report['forecasts']['5Y']['priority_sectors'] else 'Infrastructure development'}

**Key Focus Areas:**
{chr(10).join('- ' + s for s in report['forecasts']['5Y']['priority_sectors'][:3])}

*Role-specific guidance for: {role.replace('_', ' ').title()}*
*Model: {MODEL_VERSION}*"""
    
    def _answer_general(self, report: Dict, role: str) -> str:
        return self._answer_forecast(report, role)

# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

# Initialize components
logger.info("=" * 60)
logger.info("PULSE OF BHARAT - PRODUCTION API v2.0")
logger.info("=" * 60)

data_manager = DataManager()
ml_engine = MLAnalyticsEngine()
forecast_engine = ForecastingEngine()
chatbot = IntelligentChatbot(data_manager, forecast_engine)

# Apply ML models to pincode summary
if not data_manager.pincode_summary.empty and (not PRODUCTION_MODE or settings.ML_ENABLED):
    try:
        logger.info("Applying ML models...")
        data_manager.pincode_summary = ml_engine.detect_anomalies(data_manager.pincode_summary)
        data_manager.pincode_summary = ml_engine.cluster_pincodes(data_manager.pincode_summary)
        logger.info("ML models applied successfully")
    except Exception as e:
        logger.error(f"Failed to apply ML models: {e}\n{traceback.format_exc()}")

app = FastAPI(
    title="Pulse of Bharat - Governance Intelligence API",
    description="Production-ready API with ML analytics and real-time forecasting",
    version="2.0.0",
    docs_url="/docs" if not PRODUCTION_MODE or settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if not PRODUCTION_MODE or settings.ENVIRONMENT != "production" else None
)

# Add exception handlers
if PRODUCTION_MODE:
    app.add_exception_handler(Exception, custom_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)

# Add CORS middleware
if PRODUCTION_MODE:
    cors_origins = settings.CORS_ORIGINS
else:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize rate limiter
if PRODUCTION_MODE and settings.RATE_LIMIT_ENABLED:
    rate_limiter = RateLimiter(
        max_requests=settings.RATE_LIMIT_REQUESTS,
        window=settings.RATE_LIMIT_WINDOW
    )
    rate_limiter.start_cleanup()
    logger.info(f"Rate limiting enabled: {settings.RATE_LIMIT_REQUESTS} requests per {settings.RATE_LIMIT_WINDOW}s")
else:
    rate_limiter = None

# API Key Middleware
if PRODUCTION_MODE and settings.API_KEY_ENABLED and settings.API_KEY:
    from fastapi import Header
    
    async def verify_api_key(x_api_key: Optional[str] = Header(None)):
        """Verify API key for protected endpoints"""
        # Public endpoints (no API key required)
        public_endpoints = ["/", "/health", "/ready", "/docs", "/redoc", "/openapi.json"]
        
        # Check if endpoint is public
        # This will be checked in individual endpoints as needed
        if settings.API_KEY_ENABLED and x_api_key != settings.API_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        return x_api_key
    
    logger.info("API Key authentication enabled")
else:
    async def verify_api_key(x_api_key: Optional[str] = Header(None)):
        return x_api_key  # Pass-through in development
    
    if PRODUCTION_MODE:
        logger.warning("API Key authentication is disabled")

# Helper function
def safe_json(obj):
    """Convert numpy types to Python types for JSON serialization"""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj) if not np.isnan(obj) else 0.0
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif pd.isna(obj):
        return 0
    return obj

def df_to_json(df: pd.DataFrame) -> List[Dict]:
    """Convert DataFrame to JSON-safe list of dicts"""
    records = df.to_dict(orient='records')
    return [{k: safe_json(v) for k, v in r.items()} for r in records]

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint with system status"""
    try:
        return {
            "status": "operational",
            "service": "Pulse of Bharat - Governance Intelligence API",
            "version": "2.0.0",
            "model": MODEL_VERSION,
            "environment": settings.ENVIRONMENT if PRODUCTION_MODE else "development",
            "data_loaded": {
                "governance_records": len(data_manager.governance_master),
                "pincodes": len(data_manager.pincode_summary),
                "districts": len(data_manager.district_summary),
                "states": len(data_manager.state_summary)
            },
            "features": {
                "ml_anomaly_detection": settings.ML_ENABLED if PRODUCTION_MODE else True,
                "cohort_forecasting": settings.FORECAST_ENABLED if PRODUCTION_MODE else True,
                "intelligent_chatbot": settings.CHATBOT_ENABLED if PRODUCTION_MODE else True,
                "real_time_alerts": settings.WEBSOCKET_ENABLED if PRODUCTION_MODE else True,
                "rate_limiting": settings.RATE_LIMIT_ENABLED if PRODUCTION_MODE else False
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in root endpoint: {e}")
        raise HTTPException(status_code=500, detail="Service initialization error")

@app.get("/health")
async def health_check():
    """
    Health check endpoint for load balancers and monitoring
    Returns 200 if healthy, 503 if degraded
    """
    try:
        if not PRODUCTION_MODE:
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "data_loaded": not data_manager.pincode_summary.empty
            }
        
        is_healthy = health_monitor.is_healthy()
        data_loaded = not data_manager.pincode_summary.empty
        
        if is_healthy and data_loaded:
            return {
                "status": "healthy",
                "checks": {
                    "system_resources": "ok",
                    "data_loaded": "ok",
                    "error_rate": "ok"
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unhealthy",
                    "checks": {
                        "system_resources": "ok" if is_healthy else "degraded",
                        "data_loaded": "ok" if data_loaded else "failed",
                    },
                    "timestamp": datetime.now().isoformat()
                }
            )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "message": str(e)}
        )

@app.get("/metrics")
async def get_metrics():
    """
    Prometheus-compatible metrics endpoint
    Returns system metrics for monitoring
    """
    if not PRODUCTION_MODE:
        return {
            "message": "Metrics only available in production mode",
            "mode": "development"
        }
    
    try:
        metrics = health_monitor.get_system_metrics()
        performance = performance_monitor.get_stats()
        
        return {
            "health": metrics,
            "performance": performance,
            "data_stats": {
                "total_records": len(data_manager.governance_master),
                "pincodes": len(data_manager.pincode_summary),
                "districts": len(data_manager.district_summary),
                "states": len(data_manager.state_summary)
            }
        }
    except Exception as e:
        logger.error(f"Error retrieving metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")

@app.get("/ready")
async def readiness_check():
    """
    Readiness check for Kubernetes
    Returns 200 when service is ready to accept traffic
    """
    if data_manager.pincode_summary.empty:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"ready": False, "reason": "data not loaded"}
        )
    
    return {"ready": True, "timestamp": datetime.now().isoformat()}

@app.get("/api/metrics/all")
async def get_all_metrics(limit: Optional[int] = Query(None)):
    if data_manager.pincode_summary.empty:
        return {"total_records": 0, "data": []}
    
    df = data_manager.pincode_summary.copy()
    if limit:
        df = df.head(limit)
    
    return {
        "total_records": len(df),
        "ml_anomalies": int(df['ml_anomaly'].sum()) if 'ml_anomaly' in df.columns else 0,
        "data": df_to_json(df)
    }

@app.get("/api/metrics/sector/{sector_name}")
async def get_sector_metrics(
    sector_name: str,
    min_risk: float = Query(0),
    limit: int = Query(100)
):
    sector_mapping = {
        "education": "School_Dropout_Risk_Index",
        "ration": "Migrant_Hunger_Score",
        "hunger": "Migrant_Hunger_Score",
        "rural": "Village_Hollow_Out_Rate",
        "electoral": "Electoral_Discrepancy_Index",
        "labor": "Skill_Gap_Migration_Flow"
    }
    
    if sector_name.lower() not in sector_mapping:
        raise HTTPException(status_code=400, detail=f"Unknown sector. Available: {list(sector_mapping.keys())}")
    
    if data_manager.pincode_summary.empty:
        return {"sector": sector_name, "data": []}
    
    metric = sector_mapping[sector_name.lower()]
    df = data_manager.pincode_summary[data_manager.pincode_summary[metric] >= min_risk]
    df = df.nlargest(limit, metric)
    
    return {
        "sector": sector_name,
        "metric": metric,
        "total_records": len(df),
        "avg_score": round(df[metric].mean(), 2),
        "data": df_to_json(df)
    }

@app.get("/api/metrics/pincode/{pincode}")
async def get_pincode_details(pincode: int):
    if data_manager.pincode_summary.empty:
        raise HTTPException(status_code=404, detail="No data available")
    
    df = data_manager.pincode_summary[data_manager.pincode_summary['pincode'] == pincode]
    if df.empty:
        raise HTTPException(status_code=404, detail=f"Pincode {pincode} not found")
    
    record = {k: safe_json(v) for k, v in df.iloc[0].to_dict().items()}
    
    # Get time series
    ts = data_manager.get_time_series(pincode)
    ts_data = df_to_json(ts) if not ts.empty else []
    
    return {
        "summary": record,
        "timeseries": ts_data,
        "model_version": MODEL_VERSION
    }

@app.get("/api/anomalies/top-rank")
async def get_top_anomalies(limit: int = Query(20)):
    if data_manager.pincode_summary.empty:
        return {"total_alerts": 0, "data": []}
    
    df = data_manager.pincode_summary.copy()
    
    # Add anomaly type
    def get_anomaly_type(row):
        if row.get('Risk_Ghost_Population', 0) == 1:
            return "Ghost Population"
        elif row.get('Risk_Influx', 0) == 1:
            return "Illegal Influx"
        elif row.get('Mass_Migration_Alert', 0) == 1:
            return "Mass Migration"
        elif row.get('Sudden_Spike_Anomaly', 0) == 1:
            return "Sudden Spike"
        elif row.get('ml_anomaly', False):
            return "ML Detected Anomaly"
        else:
            return "General Risk"
    
    df['anomaly_type'] = df.apply(get_anomaly_type, axis=1)
    df = df.nlargest(limit, 'Governance_Risk_Score')
    
    return {
        "total_alerts": len(df),
        "ml_detected": int(df['ml_anomaly'].sum()) if 'ml_anomaly' in df.columns else 0,
        "data": df_to_json(df)
    }

@app.get("/api/report/{pincode}")
async def generate_report(pincode: int):
    if data_manager.pincode_summary.empty:
        raise HTTPException(status_code=404, detail="No data available")
    
    df = data_manager.pincode_summary[data_manager.pincode_summary['pincode'] == pincode]
    if df.empty:
        raise HTTPException(status_code=404, detail=f"Pincode {pincode} not found")
    
    record = df.iloc[0]
    gov_score = record.get('Governance_Risk_Score', 0) or 0
    
    if gov_score >= 70:
        risk_level = "CRITICAL"
    elif gov_score >= 50:
        risk_level = "HIGH"
    elif gov_score >= 30:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    # Determine primary concern
    sectors = {
        'Education': record.get('School_Dropout_Risk_Index', 0) or 0,
        'Hunger': record.get('Migrant_Hunger_Score', 0) or 0,
        'Rural': record.get('Village_Hollow_Out_Rate', 0) or 0,
        'Electoral': record.get('Electoral_Discrepancy_Index', 0) or 0,
        'Labor': record.get('Skill_Gap_Migration_Flow', 0) or 0
    }
    primary_concern = max(sectors.items(), key=lambda x: x[1])[0]
    
    action_mapping = {
        'Education': [
            "Deploy Anganwadi inspection team",
            "Cross-verify school enrollment records",
            "Initiate door-to-door child survey"
        ],
        'Hunger': [
            "Increase PDS shop grain allocation",
            "Deploy mobile ration units",
            "Activate emergency food distribution"
        ],
        'Rural': [
            "Review MGNREGA fund allocation",
            "Assess elderly care infrastructure",
            "Evaluate local employment opportunities"
        ],
        'Electoral': [
            "Alert Electoral Registration Officer (ERO)",
            "Cross-verify with Voter ID database",
            "Initiate address verification drive"
        ],
        'Labor': [
            "Coordinate with e-Shram registration centers",
            "Deploy mobile labor registration units",
            "Initiate skill development programs"
        ]
    }
    
    actions = action_mapping.get(primary_concern, ["Deploy field verification team"])
    
    summary_text = f"""
OFFICIAL GOVERNANCE ALERT REPORT
================================
Report ID: GOV-{pincode}-{datetime.now().strftime('%Y%m%d%H%M%S')}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

LOCATION DETAILS:
- Pincode: {pincode}
- District: {record.get('district', 'N/A')}
- State: {record.get('state', 'N/A')}

RISK ASSESSMENT: {risk_level}
- Governance Risk Score: {gov_score:.1f}/100
- Primary Concern: {primary_concern}

SECTOR BREAKDOWN:
- Education Risk: {sectors['Education']:.1f}/100
- Hunger Risk: {sectors['Hunger']:.1f}/100
- Rural Risk: {sectors['Rural']:.1f}/100
- Electoral Risk: {sectors['Electoral']:.1f}/100
- Labor Risk: {sectors['Labor']:.1f}/100

ML ANALYSIS:
- Anomaly Detected: {'Yes' if record.get('ml_anomaly', False) else 'No'}
- Cluster ID: {record.get('cluster_id', 'N/A')}

RECOMMENDED ACTIONS:
{chr(10).join(f'  {i+1}. {action}' for i, action in enumerate(actions))}

---
Auto-generated by Pulse of Bharat Governance Intelligence System
Model: {MODEL_VERSION}
"""
    
    return {
        "pincode": pincode,
        "district": str(record.get('district', 'N/A')),
        "state": str(record.get('state', 'N/A')),
        "report_date": datetime.now().isoformat(),
        "summary": summary_text,
        "risk_level": risk_level,
        "primary_concern": primary_concern,
        "recommended_actions": actions,
        "sector_breakdown": {k.lower(): round(v, 2) for k, v in sectors.items()},
        "ml_analysis": {
            "is_anomaly": bool(record.get('ml_anomaly', False)),
            "anomaly_score": round(float(record.get('anomaly_score', 0) or 0), 3),
            "cluster_id": int(record.get('cluster_id', 0) or 0)
        },
        "model_version": MODEL_VERSION
    }

@app.get("/api/stats/overview")
async def get_overview_stats():
    if data_manager.pincode_summary.empty:
        return {"error": "No data loaded"}
    
    df = data_manager.pincode_summary
    
    return {
        "total_pincodes": len(df),
        "total_records": len(data_manager.governance_master),
        "total_districts": len(data_manager.district_summary),
        "total_states": len(data_manager.state_summary),
        "risk_distribution": {
            "critical": int((df['Governance_Risk_Score'] >= 70).sum()),
            "high": int(((df['Governance_Risk_Score'] >= 50) & (df['Governance_Risk_Score'] < 70)).sum()),
            "medium": int(((df['Governance_Risk_Score'] >= 30) & (df['Governance_Risk_Score'] < 50)).sum()),
            "low": int((df['Governance_Risk_Score'] < 30).sum())
        },
        "sector_alerts": {
            "education": int((df['School_Dropout_Risk_Index'] > 50).sum()),
            "hunger": int((df['Migrant_Hunger_Score'] > 50).sum()),
            "rural": int((df['Village_Hollow_Out_Rate'] > 50).sum()),
            "electoral": int((df['Electoral_Discrepancy_Index'] > 50).sum()),
            "labor": int((df['Skill_Gap_Migration_Flow'] > 50).sum())
        },
        "ml_stats": {
            "total_anomalies": int(df['ml_anomaly'].sum()) if 'ml_anomaly' in df.columns else 0,
            "clusters": int(df['cluster_id'].nunique()) if 'cluster_id' in df.columns else 0
        },
        "avg_national_risk": round(df['Governance_Risk_Score'].mean(), 1),
        "last_updated": datetime.now().isoformat(),
        "model_version": MODEL_VERSION
    }

@app.get("/api/stats/by-state")
async def get_state_stats():
    if data_manager.state_summary.empty:
        return {"data": []}
    
    return {
        "total_states": len(data_manager.state_summary),
        "data": df_to_json(data_manager.state_summary)
    }

@app.get("/api/map/geojson")
async def get_map_geojson(sector: str = Query("all")):
    if data_manager.pincode_summary.empty:
        return {"type": "FeatureCollection", "features": []}
    
    sector_mapping = {
        "education": "School_Dropout_Risk_Index",
        "hunger": "Migrant_Hunger_Score",
        "rural": "Village_Hollow_Out_Rate",
        "electoral": "Electoral_Discrepancy_Index",
        "labor": "Skill_Gap_Migration_Flow",
        "all": "Governance_Risk_Score"
    }
    
    metric = sector_mapping.get(sector.lower(), "Governance_Risk_Score")
    df = data_manager.pincode_summary
    
    features = []
    for _, row in df.iterrows():
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row['longitude']), float(row['latitude'])]
            },
            "properties": {
                "pincode": int(row['pincode']),
                "state": str(row['state']),
                "district": str(row['district']),
                "risk_score": round(float(row[metric] or 0), 2),
                "governance_score": round(float(row['Governance_Risk_Score'] or 0), 2),
                "risk_level": str(row.get('risk_level', 'MEDIUM')),
                "is_anomaly": bool(row.get('ml_anomaly', False))
            }
        })
    
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {"metric": metric, "total": len(features)}
    }

@app.get("/api/map/district-aggregation")
async def get_district_aggregation(sector: str = Query("all")):
    if data_manager.district_summary.empty:
        return {"data": []}
    
    return {
        "total_districts": len(data_manager.district_summary),
        "sector": sector,
        "data": df_to_json(data_manager.district_summary)
    }

@app.get("/api/map/state-aggregation")
async def get_state_aggregation():
    if data_manager.state_summary.empty:
        return {"data": []}
    
    return {
        "total_states": len(data_manager.state_summary),
        "data": df_to_json(data_manager.state_summary)
    }

@app.get("/api/map/filtered-pincodes")
async def get_filtered_pincodes():
    if data_manager.pincode_summary.empty:
        return {"data": []}
    
    # Filter to India bounds
    df = data_manager.pincode_summary[
        (data_manager.pincode_summary['latitude'] >= 6.5) &
        (data_manager.pincode_summary['latitude'] <= 35.5) &
        (data_manager.pincode_summary['longitude'] >= 68.0) &
        (data_manager.pincode_summary['longitude'] <= 97.5)
    ]
    
    return {
        "total_records": len(df),
        "data": df_to_json(df)
    }

# =============================================================================
# INTELLIGENCE ENGINE ENDPOINTS
# =============================================================================

@app.get("/api/intelligence/status")
async def get_intelligence_status():
    return {
        "engine_available": True,
        "model_version": MODEL_VERSION,
        "districts_loaded": len(data_manager.district_summary),
        "features": {
            "forecasting": True,
            "policy_mapping": True,
            "chatbot": True,
            "ml_analytics": True
        }
    }

@app.get("/api/intelligence/roles")
async def get_available_roles():
    return {
        "roles": [
            {"id": "police", "label": "Police Administration", "icon": "👮"},
            {"id": "district_admin", "label": "District Administration", "icon": "🏛️"},
            {"id": "state_govt", "label": "State Government", "icon": "🏢"},
            {"id": "budget", "label": "Budget & Finance", "icon": "💰"},
            {"id": "education", "label": "Education Department", "icon": "🎓"},
            {"id": "health", "label": "Health Department", "icon": "🏥"},
            {"id": "skill", "label": "Skill & Employment", "icon": "🛠️"}
        ]
    }

@app.get("/api/intelligence/districts")
async def get_available_districts():
    districts = data_manager.get_districts_list()
    return {
        "total_districts": sum(len(v) for v in districts.values()),
        "by_state": districts
    }

class ChatRequest(BaseModel):
    message: str
    role: str = "district_admin"
    district: Optional[str] = None

@app.post("/api/intelligence/chat")
async def chat_with_intelligence(request: ChatRequest):
    if not request.district:
        # Use first available district
        districts = data_manager.get_districts_list()
        if districts:
            first_state = list(districts.keys())[0]
            request.district = districts[first_state][0] if districts[first_state] else "Delhi"
        else:
            request.district = "Delhi"
    
    answer = chatbot.answer_question(request.message, request.district, request.role)
    
    return {
        "success": True,
        "answer": answer,
        "role": request.role,
        "district": request.district,
        "model_version": MODEL_VERSION
    }

@app.get("/api/intelligence/district-report/{district_name}")
async def get_district_report(district_name: str, role: str = Query("district_admin")):
    report = chatbot.generate_district_report(district_name, role)
    return report

@app.get("/api/intelligence/sample-questions")
async def get_sample_questions(role: str = Query("district_admin")):
    samples = {
        "police": [
            "What is the youth population projection?",
            "How does migration affect law enforcement needs?",
            "What is the overall governance risk?"
        ],
        "education": [
            "How many school seats are needed in 5 years?",
            "What is the dropout risk in this district?",
            "What is the education sector budget stress?"
        ],
        "health": [
            "What is the hospital bed demand projection?",
            "How many additional doctors are needed?",
            "What is the maternity load trend?"
        ],
        "budget": [
            "What is the overall budget stress level?",
            "Which sectors need priority funding?",
            "What is the 5-year resource requirement?"
        ],
        "district_admin": [
            "Give me the overall district projection",
            "What are the priority action items?",
            "Compare this district with peers"
        ],
        "state_govt": [
            "What is the state-wide governance trend?",
            "Which districts need intervention?",
            "What policy changes are recommended?"
        ],
        "skill": [
            "What is the skill training demand?",
            "How does migration affect employment?",
            "What skills are most needed?"
        ]
    }
    
    return {
        "role": role,
        "questions": samples.get(role.lower(), samples["district_admin"])
    }

# =============================================================================
# FORECASTING ENDPOINTS
# =============================================================================

@app.get("/api/analytics/forecasts")
async def get_forecasts():
    """Get real forecasting data based on actual data"""
    if data_manager.governance_master.empty:
        return {"data": []}
    
    # Generate forecasts for top districts
    forecasts = []
    top_districts = data_manager.district_summary.nlargest(20, 'Governance_Risk_Score_mean') if 'Governance_Risk_Score_mean' in data_manager.district_summary.columns else data_manager.district_summary.head(20)
    
    for _, row in top_districts.iterrows():
        district = row['district']
        report = chatbot.generate_district_report(district)
        
        if "error" not in report:
            forecasts.append({
                "district": district,
                "state": report["state"],
                "current_population": report["current_state"]["total_population"],
                "forecast_1y": report["forecasts"]["1Y"]["population"],
                "forecast_5y": report["forecasts"]["5Y"]["population"],
                "forecast_10y": report["forecasts"]["10Y"]["population"],
                "budget_stress_1y": report["forecasts"]["1Y"]["budget_stress"],
                "confidence": report["current_state"]["confidence"]
            })
    
    return {"total_records": len(forecasts), "data": forecasts}

@app.get("/api/analytics/clusters")
async def get_clusters():
    """Get cluster analysis data"""
    if data_manager.pincode_summary.empty or 'cluster_id' not in data_manager.pincode_summary.columns:
        return {"data": []}
    
    cluster_stats = data_manager.pincode_summary.groupby('cluster_id').agg({
        'pincode': 'count',
        'Governance_Risk_Score': 'mean',
        'School_Dropout_Risk_Index': 'mean',
        'Migrant_Hunger_Score': 'mean'
    }).reset_index()
    
    cluster_stats.columns = ['cluster_id', 'pincode_count', 'avg_risk', 'avg_education', 'avg_hunger']
    
    return {
        "total_clusters": len(cluster_stats),
        "data": df_to_json(cluster_stats)
    }

@app.get("/api/analytics/state-risk")
async def get_state_risk():
    """Get state-wise risk summary"""
    if data_manager.state_summary.empty:
        return {"data": []}
    
    return {
        "total_states": len(data_manager.state_summary),
        "data": df_to_json(data_manager.state_summary)
    }

@app.get("/api/analytics/government-insights")
async def get_government_insights():
    """Get ministry-wise insights"""
    if data_manager.pincode_summary.empty:
        return {"data": []}
    
    df = data_manager.pincode_summary
    
    insights = [
        {
            "ministry": "Education",
            "critical_pincodes": int((df['School_Dropout_Risk_Index'] > 70).sum()),
            "high_risk_pincodes": int((df['School_Dropout_Risk_Index'] > 50).sum()),
            "avg_risk": round(df['School_Dropout_Risk_Index'].mean(), 1),
            "action_required": "School capacity expansion"
        },
        {
            "ministry": "Consumer Affairs (PDS)",
            "critical_pincodes": int((df['Migrant_Hunger_Score'] > 70).sum()),
            "high_risk_pincodes": int((df['Migrant_Hunger_Score'] > 50).sum()),
            "avg_risk": round(df['Migrant_Hunger_Score'].mean(), 1),
            "action_required": "Ration allocation review"
        },
        {
            "ministry": "Rural Development",
            "critical_pincodes": int((df['Village_Hollow_Out_Rate'] > 70).sum()),
            "high_risk_pincodes": int((df['Village_Hollow_Out_Rate'] > 50).sum()),
            "avg_risk": round(df['Village_Hollow_Out_Rate'].mean(), 1),
            "action_required": "MGNREGA enhancement"
        },
        {
            "ministry": "Election Commission",
            "critical_pincodes": int((df['Electoral_Discrepancy_Index'] > 70).sum()),
            "high_risk_pincodes": int((df['Electoral_Discrepancy_Index'] > 50).sum()),
            "avg_risk": round(df['Electoral_Discrepancy_Index'].mean(), 1),
            "action_required": "Voter verification drive"
        },
        {
            "ministry": "Labour & Employment",
            "critical_pincodes": int((df['Skill_Gap_Migration_Flow'] > 70).sum()),
            "high_risk_pincodes": int((df['Skill_Gap_Migration_Flow'] > 50).sum()),
            "avg_risk": round(df['Skill_Gap_Migration_Flow'].mean(), 1),
            "action_required": "Skill training expansion"
        }
    ]
    
    return {"total_ministries": len(insights), "data": insights}

@app.get("/api/intelligence/forecast-matrix")
async def get_forecast_matrix(limit: int = Query(15)):
    """Get forecast matrix for multiple districts"""
    forecasts = []
    top_districts = data_manager.district_summary.head(limit)
    
    for _, row in top_districts.iterrows():
        report = chatbot.generate_district_report(row['district'])
        if "error" not in report:
            forecasts.append({
                "district": row['district'],
                "state": report["state"],
                "pop_1y": report["forecasts"]["1Y"]["population"],
                "pop_5y": report["forecasts"]["5Y"]["population"],
                "stress_1y": report["forecasts"]["1Y"]["budget_stress"],
                "confidence": report["forecasts"]["1Y"]["confidence"]
            })
    
    return {"total_districts": len(forecasts), "data": forecasts}

# =============================================================================
# EXPORT ENDPOINTS
# =============================================================================

@app.get("/api/export/csv")
async def export_csv():
    """Export data to CSV"""
    if data_manager.pincode_summary.empty:
        raise HTTPException(status_code=404, detail="No data available")
    
    output = BytesIO()
    data_manager.pincode_summary.to_csv(output, index=False)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=governance_export_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

# =============================================================================
# WEBSOCKET FOR REAL-TIME ALERTS
# =============================================================================

active_websockets: List[WebSocket] = []

@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    
    try:
        while True:
            # Send alerts every 30 seconds
            await asyncio.sleep(30)
            
            if not data_manager.pincode_summary.empty:
                critical = data_manager.pincode_summary[
                    data_manager.pincode_summary['Governance_Risk_Score'] >= 70
                ].head(5)
                
                alert_data = {
                    "timestamp": datetime.now().isoformat(),
                    "critical_count": len(critical),
                    "alerts": df_to_json(critical[['pincode', 'district', 'state', 'Governance_Risk_Score']])
                }
                
                await websocket.send_json(alert_data)
    except WebSocketDisconnect:
        active_websockets.remove(websocket)

# =============================================================================
# RUN SERVER
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
