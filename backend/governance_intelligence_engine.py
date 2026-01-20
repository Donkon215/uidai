"""
Governance Intelligence Engine
==============================
Implements the 7 Laws of System for demographic forecasting and policy intelligence.

Laws Implemented:
1. Separation of Intelligence (LLM = Interpreter, not Predictor)
2. No Raw Data Touch by LLM (only aggregated signals)
3. Forecast by Transition (cohort-based projection)
4. Multi-Resolution Truth (1Y, 5Y, 10Y)
5. Confidence as First-Class Data
6. Policy Mapping (Police, Schools, Health, Budget)
7. Explainability > Accuracy

Author: Pulse of Bharat Team
Version: DEMOG_COHORT_v1.0
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json

# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

MODEL_VERSION = "DEMOG_COHORT_v1.0"
CURRENT_YEAR = 2026

# Transition rates (configurable, auditable)
TRANSITION_CONFIG = {
    "version": "TRANS_v1.0",
    "assumptions": [
        "stable_birth_rate",
        "migration_rate_from_historical",
        "mortality_rate_national_average"
    ],
    "rates": {
        "child_to_student": 0.91,      # 0-5 → 5-17
        "student_to_workforce": 0.83,   # 5-17 → 17-35
        "out_migration_rate": 0.12,     # Net outward migration for youth
        "family_formation_rate": 0.35,  # Adults forming families
        "fertility_rate": 0.6,          # Children per family (5-year horizon)
    }
}

# Policy mapping ratios
POLICY_RATIOS = {
    "police_per_1000": 2.2,
    "school_seats_per_child": 1.0,
    "hospital_beds_per_1000": 1.3,
    "doctors_per_1000": 0.8,
    "skill_centers_per_10000_youth": 0.5,
}

# =============================================================================
# DATA CLASSES
# =============================================================================

class DataQuality(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CRITICAL = "critical"

@dataclass
class DistrictStateVector:
    """State vector for a district at a point in time"""
    district: str
    state: str
    year: int
    population_0_5: int
    population_5_17: int
    population_17_35: int
    population_35_plus: int
    new_registrations: int
    migration_rate: float
    youth_density: float
    data_quality: str
    confidence: float

@dataclass
class ForecastResult:
    """Result of demographic forecast"""
    district: str
    state: str
    base_year: int
    forecast_year: int
    horizon: str  # "1Y", "5Y", "10Y"
    predicted_0_5: int
    predicted_5_17: int
    predicted_17_35: int
    predicted_35_plus: int
    total_predicted: int
    confidence: float
    data_quality: str
    model_version: str
    assumptions: List[str]

@dataclass
class PolicyImpact:
    """Policy impact assessment for a district"""
    district: str
    state: str
    year: int
    horizon: str
    # Police
    police_force_delta: int
    youth_density_index: float
    law_order_stress: str
    # Education
    school_seats_needed: int
    dropout_risk_index: float
    education_budget_index: float
    # Health
    hospital_beds_delta: float
    doctor_gap: float
    maternity_load_index: float
    # Skills
    skill_training_demand: int
    migration_skill_loss: float
    # Budget
    overall_budget_stress: str
    priority_sectors: List[str]
    # Audit
    trigger_metrics: List[str]
    confidence: float
    model_version: str

@dataclass
class DataQualityReport:
    """Data quality assessment for a district"""
    district: str
    state: str
    year: int
    overall_quality: str
    missing_days_pct: float
    registration_spikes: int
    coverage_consistency: float
    issues: List[str]
    recommendations: List[str]

# =============================================================================
# DATA QUALITY ENGINE
# =============================================================================

class DataQualityEngine:
    """
    Assesses data quality before forecasting.
    Govt systems NEVER trust data blindly.
    """
    
    def __init__(self, expected_days: int = 365):
        self.expected_days = expected_days
    
    def assess_quality(self, df: pd.DataFrame, district: str, year: int) -> DataQualityReport:
        """Assess data quality for a district-year"""
        issues = []
        recommendations = []
        
        # Filter data
        district_data = df[(df['district'] == district) & (df['year'] == year)] if 'year' in df.columns else df[df['district'] == district]
        
        if len(district_data) == 0:
            return DataQualityReport(
                district=district,
                state="Unknown",
                year=year,
                overall_quality="critical",
                missing_days_pct=100.0,
                registration_spikes=0,
                coverage_consistency=0.0,
                issues=["No data available for this district-year"],
                recommendations=["Obtain data from alternative sources"]
            )
        
        state = district_data['state'].iloc[0] if 'state' in district_data.columns else "Unknown"
        
        # Check 1: Missing days
        actual_days = len(district_data)
        missing_pct = max(0, (self.expected_days - actual_days) / self.expected_days * 100)
        if missing_pct > 30:
            issues.append(f"missing_days_{missing_pct:.0f}%")
            recommendations.append("Investigate data collection gaps")
        
        # Check 2: Registration spikes (anomalies)
        if 'new_registrations' in district_data.columns:
            reg_values = district_data['new_registrations'].dropna()
            if len(reg_values) > 0:
                mean_reg = reg_values.mean()
                std_reg = reg_values.std()
                spikes = len(reg_values[reg_values > mean_reg + 3 * std_reg]) if std_reg > 0 else 0
                if spikes > 5:
                    issues.append(f"registration_spikes_{spikes}")
                    recommendations.append("Review spike days for data entry errors")
            else:
                spikes = 0
        else:
            spikes = 0
        
        # Check 3: Coverage consistency
        required_fields = ['age_0_5', 'age_5_17', 'age_17_plus']
        available_fields = [f for f in required_fields if f in district_data.columns]
        coverage = len(available_fields) / len(required_fields) if required_fields else 1.0
        if coverage < 0.8:
            issues.append("incomplete_age_buckets")
            recommendations.append("Ensure all age buckets are collected")
        
        # Determine overall quality
        if missing_pct > 50 or coverage < 0.5:
            quality = "critical"
        elif missing_pct > 30 or spikes > 10 or coverage < 0.8:
            quality = "low"
        elif missing_pct > 15 or spikes > 5:
            quality = "medium"
        else:
            quality = "high"
        
        return DataQualityReport(
            district=district,
            state=state,
            year=year,
            overall_quality=quality,
            missing_days_pct=missing_pct,
            registration_spikes=spikes,
            coverage_consistency=coverage,
            issues=issues if issues else ["No major issues detected"],
            recommendations=recommendations if recommendations else ["Data quality acceptable"]
        )

# =============================================================================
# SIGNAL EXTRACTION ENGINE
# =============================================================================

class SignalExtractionEngine:
    """
    Extracts meaningful signals from aggregated district data.
    Outputs: birth rate proxy, migration rate, youth growth, registration velocity
    """
    
    def extract_signals(self, df: pd.DataFrame, district: str) -> Dict:
        """Extract demographic signals for a district"""
        district_data = df[df['district'] == district] if 'district' in df.columns else df
        
        if len(district_data) == 0:
            return self._empty_signals(district)
        
        signals = {
            "district": district,
            "state": district_data['state'].iloc[0] if 'state' in district_data.columns else "Unknown",
            "year": CURRENT_YEAR,
        }
        
        # Birth rate proxy (0-5 population growth)
        if 'age_0_5' in district_data.columns:
            age_0_5 = district_data['age_0_5'].sum()
            signals['birth_rate_proxy'] = age_0_5 / len(district_data) if len(district_data) > 0 else 0
        else:
            signals['birth_rate_proxy'] = 0
        
        # Youth growth rate
        if 'age_5_17' in district_data.columns:
            age_5_17 = district_data['age_5_17'].sum()
            signals['youth_growth'] = age_5_17 / len(district_data) if len(district_data) > 0 else 0
        else:
            signals['youth_growth'] = 0
        
        # Registration velocity
        if 'new_registrations' in district_data.columns:
            total_reg = district_data['new_registrations'].sum()
            signals['registration_velocity'] = total_reg / len(district_data) if len(district_data) > 0 else 0
        else:
            signals['registration_velocity'] = 0
        
        # Migration rate estimation (negative = outward)
        total_pop = sum([
            district_data.get('age_0_5', pd.Series([0])).sum(),
            district_data.get('age_5_17', pd.Series([0])).sum(),
            district_data.get('age_17_plus', pd.Series([0])).sum()
        ])
        signals['migration_rate'] = -0.08  # Default estimate, should be calculated from historical data
        
        # Youth density
        if 'age_17_plus' in district_data.columns and total_pop > 0:
            youth = district_data['age_17_plus'].sum()
            signals['youth_density'] = youth / total_pop
        else:
            signals['youth_density'] = 0.3  # Default
        
        return signals
    
    def _empty_signals(self, district: str) -> Dict:
        return {
            "district": district,
            "state": "Unknown",
            "year": CURRENT_YEAR,
            "birth_rate_proxy": 0,
            "youth_growth": 0,
            "registration_velocity": 0,
            "migration_rate": 0,
            "youth_density": 0
        }

# =============================================================================
# TRANSITION FORECAST ENGINE (CORE)
# =============================================================================

class TransitionForecastEngine:
    """
    Core demographic forecasting using transition-based cohort projection.
    
    Formula: State(t+n) = State(t) × Transition_Matrix
    
    This is world-standard demography logic used by census worldwide.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or TRANSITION_CONFIG
        self.rates = self.config['rates']
    
    def create_state_vector(self, df: pd.DataFrame, district: str, quality_report: DataQualityReport) -> DistrictStateVector:
        """Create current state vector for a district"""
        district_data = df[df['district'] == district] if 'district' in df.columns else df
        
        if len(district_data) == 0:
            return None
        
        state = district_data['state'].iloc[0] if 'state' in district_data.columns else "Unknown"
        
        # Aggregate population by age
        pop_0_5 = int(district_data['age_0_5'].sum()) if 'age_0_5' in district_data.columns else 0
        pop_5_17 = int(district_data['age_5_17'].sum()) if 'age_5_17' in district_data.columns else 0
        pop_17_35 = int(district_data['age_17_plus'].sum() * 0.5) if 'age_17_plus' in district_data.columns else 0  # Estimate
        pop_35_plus = int(district_data['age_17_plus'].sum() * 0.5) if 'age_17_plus' in district_data.columns else 0
        
        new_reg = int(district_data['new_registrations'].sum()) if 'new_registrations' in district_data.columns else 0
        
        total_pop = pop_0_5 + pop_5_17 + pop_17_35 + pop_35_plus
        youth_density = (pop_17_35) / total_pop if total_pop > 0 else 0.3
        
        # Calculate confidence from data quality
        confidence_map = {"high": 0.90, "medium": 0.74, "low": 0.55, "critical": 0.30}
        confidence = confidence_map.get(quality_report.overall_quality, 0.50)
        
        return DistrictStateVector(
            district=district,
            state=state,
            year=CURRENT_YEAR,
            population_0_5=pop_0_5,
            population_5_17=pop_5_17,
            population_17_35=pop_17_35,
            population_35_plus=pop_35_plus,
            new_registrations=new_reg,
            migration_rate=-0.08,  # Default
            youth_density=youth_density,
            data_quality=quality_report.overall_quality,
            confidence=confidence
        )
    
    def forecast(self, state_vector: DistrictStateVector, horizon_years: int) -> ForecastResult:
        """
        Project population forward using transition matrix.
        
        Transition logic:
        - 0-5 → 5-17 (after 5 years)
        - 5-17 → 17-35 (after 12 years)
        - 17-35 → 35+ or migration out
        """
        if state_vector is None:
            return None
        
        # Determine horizon label
        if horizon_years <= 1:
            horizon = "1Y"
        elif horizon_years <= 5:
            horizon = "5Y"
        else:
            horizon = "10Y"
        
        # Get current populations
        current = {
            "0_5": state_vector.population_0_5,
            "5_17": state_vector.population_5_17,
            "17_35": state_vector.population_17_35,
            "35_plus": state_vector.population_35_plus
        }
        
        # Apply transitions based on horizon
        if horizon_years <= 1:
            # Minimal change, mainly new registrations impact
            predicted = {
                "0_5": int(current["0_5"] * 1.02),  # Small growth
                "5_17": int(current["5_17"] * 1.01),
                "17_35": int(current["17_35"] * (1 - self.rates['out_migration_rate'] * 0.1)),
                "35_plus": int(current["35_plus"] * 1.01)
            }
        elif horizon_years <= 5:
            # 5-year projection: cohort transitions
            predicted = {
                "0_5": int(current["17_35"] * self.rates['family_formation_rate'] * self.rates['fertility_rate']),
                "5_17": int(current["0_5"] * self.rates['child_to_student'] + current["5_17"] * 0.6),
                "17_35": int(current["5_17"] * self.rates['student_to_workforce'] * (1 - self.rates['out_migration_rate'])),
                "35_plus": int(current["17_35"] * 0.3 + current["35_plus"] * 0.95)
            }
        else:
            # 10-year projection: double transition
            intermediate = {
                "0_5": int(current["17_35"] * self.rates['family_formation_rate'] * self.rates['fertility_rate']),
                "5_17": int(current["0_5"] * self.rates['child_to_student']),
                "17_35": int(current["5_17"] * self.rates['student_to_workforce']),
                "35_plus": int(current["17_35"] * 0.5 + current["35_plus"] * 0.9)
            }
            # Second transition
            predicted = {
                "0_5": int(intermediate["17_35"] * self.rates['family_formation_rate'] * self.rates['fertility_rate']),
                "5_17": int(intermediate["0_5"] * self.rates['child_to_student'] + intermediate["5_17"] * 0.4),
                "17_35": int(intermediate["5_17"] * self.rates['student_to_workforce'] * (1 - self.rates['out_migration_rate'])),
                "35_plus": int(intermediate["17_35"] * 0.4 + intermediate["35_plus"] * 0.85)
            }
        
        # Adjust confidence for longer horizons
        confidence_decay = {1: 1.0, 5: 0.85, 10: 0.70}
        horizon_key = min(horizon_years, 10)
        adjusted_confidence = state_vector.confidence * confidence_decay.get(horizon_key, 0.70)
        
        return ForecastResult(
            district=state_vector.district,
            state=state_vector.state,
            base_year=state_vector.year,
            forecast_year=state_vector.year + horizon_years,
            horizon=horizon,
            predicted_0_5=predicted["0_5"],
            predicted_5_17=predicted["5_17"],
            predicted_17_35=predicted["17_35"],
            predicted_35_plus=predicted["35_plus"],
            total_predicted=sum(predicted.values()),
            confidence=round(adjusted_confidence, 2),
            data_quality=state_vector.data_quality,
            model_version=MODEL_VERSION,
            assumptions=self.config['assumptions']
        )

# =============================================================================
# POLICY MAPPING ENGINE
# =============================================================================

class PolicyMappingEngine:
    """
    Maps demographic forecasts to policy impacts.
    
    Outputs:
    - Police force need
    - School demand
    - Hospital load
    - Budget stress indicators
    """
    
    def __init__(self, ratios: Dict = None):
        self.ratios = ratios or POLICY_RATIOS
    
    def calculate_impact(self, current: DistrictStateVector, forecast: ForecastResult) -> PolicyImpact:
        """Calculate policy impact from forecast"""
        if current is None or forecast is None:
            return None
        
        # Population deltas
        delta_youth = forecast.predicted_17_35 - current.population_17_35
        delta_children = forecast.predicted_5_17 - current.population_5_17
        delta_infants = forecast.predicted_0_5 - current.population_0_5
        total_delta = forecast.total_predicted - (current.population_0_5 + current.population_5_17 + 
                                                   current.population_17_35 + current.population_35_plus)
        
        # Police impact
        police_delta = int(total_delta / 1000 * self.ratios['police_per_1000'])
        youth_density_index = forecast.predicted_17_35 / forecast.total_predicted if forecast.total_predicted > 0 else 0.3
        
        if youth_density_index > 0.35 and delta_youth > 0:
            law_order_stress = "HIGH"
        elif youth_density_index > 0.30:
            law_order_stress = "MEDIUM"
        else:
            law_order_stress = "LOW"
        
        # Education impact
        school_seats = int(delta_children * self.ratios['school_seats_per_child'])
        dropout_risk = min(1.0, abs(delta_youth) / max(delta_children, 1) * 0.1)
        education_budget_idx = 1.0 + (delta_children / max(current.population_5_17, 1))
        
        # Health impact
        hospital_beds = (total_delta / 1000) * self.ratios['hospital_beds_per_1000']
        doctor_gap = (total_delta / 1000) * self.ratios['doctors_per_1000']
        maternity_load = delta_infants / max(current.population_0_5, 1)
        
        # Skill demand
        skill_demand = int(delta_youth / 10000 * self.ratios['skill_centers_per_10000_youth'])
        migration_skill_loss = abs(current.migration_rate) if current.migration_rate < 0 else 0
        
        # Budget stress
        if education_budget_idx > 1.15 or police_delta > 50:
            budget_stress = "HIGH"
        elif education_budget_idx > 1.05 or police_delta > 20:
            budget_stress = "MEDIUM"
        else:
            budget_stress = "LOW"
        
        # Priority sectors
        priorities = []
        if police_delta > 20 or law_order_stress == "HIGH":
            priorities.append("Police & Law Enforcement")
        if school_seats > 100:
            priorities.append("Primary Education")
        if hospital_beds > 5:
            priorities.append("Healthcare Infrastructure")
        if skill_demand > 2:
            priorities.append("Skill Development")
        
        # Trigger metrics for audit
        triggers = []
        if delta_youth > 0:
            triggers.append("youth_density ↑")
        if current.migration_rate < -0.1:
            triggers.append("migration_spike ↑")
        if delta_children > current.population_5_17 * 0.1:
            triggers.append("child_population ↑")
        
        return PolicyImpact(
            district=forecast.district,
            state=forecast.state,
            year=forecast.forecast_year,
            horizon=forecast.horizon,
            police_force_delta=police_delta,
            youth_density_index=round(youth_density_index, 2),
            law_order_stress=law_order_stress,
            school_seats_needed=max(0, school_seats),
            dropout_risk_index=round(dropout_risk, 2),
            education_budget_index=round(education_budget_idx, 2),
            hospital_beds_delta=round(hospital_beds, 1),
            doctor_gap=round(doctor_gap, 1),
            maternity_load_index=round(maternity_load, 2),
            skill_training_demand=max(0, skill_demand),
            migration_skill_loss=round(migration_skill_loss, 2),
            overall_budget_stress=budget_stress,
            priority_sectors=priorities if priorities else ["General Maintenance"],
            trigger_metrics=triggers if triggers else ["stable_growth"],
            confidence=forecast.confidence,
            model_version=MODEL_VERSION
        )

# =============================================================================
# DISTRICT COMPARISON ENGINE
# =============================================================================

class DistrictComparisonEngine:
    """
    Compares districts with peer groups.
    Govt asks: "How is Lucknow compared to similar districts?"
    """
    
    def __init__(self, all_forecasts: List[ForecastResult] = None):
        self.forecasts = all_forecasts or []
    
    def find_peer_group(self, district: str, state: str) -> List[str]:
        """Find similar districts based on state and population size"""
        # Simple peer grouping by same state
        peers = [f.district for f in self.forecasts 
                 if f.state == state and f.district != district]
        return peers[:5]  # Top 5 peers
    
    def compare(self, district: str, state: str) -> Dict:
        """Compare district with peers"""
        district_forecast = next((f for f in self.forecasts if f.district == district), None)
        if not district_forecast:
            return {"error": "District forecast not found"}
        
        peers = self.find_peer_group(district, state)
        peer_forecasts = [f for f in self.forecasts if f.district in peers]
        
        if not peer_forecasts:
            return {
                "district": district,
                "peer_group": [],
                "comparison": "No peer data available"
            }
        
        # Calculate rankings
        all_youth = [(f.district, f.predicted_17_35) for f in [district_forecast] + peer_forecasts]
        all_youth.sort(key=lambda x: x[1], reverse=True)
        youth_rank = next((i + 1 for i, (d, _) in enumerate(all_youth) if d == district), 0)
        
        all_growth = [(f.district, f.total_predicted) for f in [district_forecast] + peer_forecasts]
        all_growth.sort(key=lambda x: x[1], reverse=True)
        growth_rank = next((i + 1 for i, (d, _) in enumerate(all_growth) if d == district), 0)
        
        return {
            "district": district,
            "peer_group": peers,
            "youth_growth_rank": youth_rank,
            "population_growth_rank": growth_rank,
            "total_in_comparison": len(all_youth)
        }

# =============================================================================
# GOVERNANCE INTELLIGENCE ORCHESTRATOR
# =============================================================================

class GovernanceIntelligenceEngine:
    """
    Main orchestrator for the Governance Intelligence system.
    
    Pipeline: Data → Quality → Signal → Transition → Scenario → Policy → Explanation
    """
    
    def __init__(self):
        self.data_quality_engine = DataQualityEngine()
        self.signal_engine = SignalExtractionEngine()
        self.forecast_engine = TransitionForecastEngine()
        self.policy_engine = PolicyMappingEngine()
        self.comparison_engine = None  # Initialized after forecasts
    
    def process_district(self, df: pd.DataFrame, district: str, horizons: List[int] = [1, 5, 10]) -> Dict:
        """
        Full processing pipeline for a single district.
        
        Returns comprehensive governance intelligence.
        """
        results = {
            "district": district,
            "processing_timestamp": datetime.now().isoformat(),
            "model_version": MODEL_VERSION,
        }
        
        # Step 1: Data Quality Assessment
        quality_report = self.data_quality_engine.assess_quality(df, district, CURRENT_YEAR)
        results["data_quality"] = asdict(quality_report)
        
        # Step 2: Signal Extraction
        signals = self.signal_engine.extract_signals(df, district)
        results["signals"] = signals
        
        # Step 3: Create State Vector
        state_vector = self.forecast_engine.create_state_vector(df, district, quality_report)
        if state_vector:
            results["current_state"] = asdict(state_vector)
        else:
            results["error"] = "Could not create state vector"
            return results
        
        # Step 4: Forecasts for all horizons
        forecasts = {}
        policy_impacts = {}
        for horizon in horizons:
            forecast = self.forecast_engine.forecast(state_vector, horizon)
            if forecast:
                forecasts[f"{horizon}Y"] = asdict(forecast)
                
                # Step 5: Policy Mapping
                impact = self.policy_engine.calculate_impact(state_vector, forecast)
                if impact:
                    policy_impacts[f"{horizon}Y"] = asdict(impact)
        
        results["forecasts"] = forecasts
        results["policy_impacts"] = policy_impacts
        
        return results
    
    def process_all_districts(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """Process all districts in the dataset"""
        if 'district' not in df.columns:
            return {"error": "No district column in data"}
        
        districts = df['district'].unique()
        all_results = {}
        
        for district in districts:
            try:
                all_results[district] = self.process_district(df, district)
            except Exception as e:
                all_results[district] = {"error": str(e)}
        
        return all_results
    
    def get_forecast_matrix(self, df: pd.DataFrame, districts: List[str] = None) -> pd.DataFrame:
        """
        Generate the Forecast Matrix for reporting.
        
        Rows: Districts
        Columns: Metrics × Horizons
        """
        if districts is None:
            districts = df['district'].unique()[:20]  # Limit for performance
        
        matrix_data = []
        for district in districts:
            result = self.process_district(df, district)
            
            if "error" not in result and "forecasts" in result:
                for horizon, forecast in result["forecasts"].items():
                    row = {
                        "district": district,
                        "state": forecast.get("state", "Unknown"),
                        "horizon": horizon,
                        "predicted_0_5": forecast.get("predicted_0_5", 0),
                        "predicted_5_17": forecast.get("predicted_5_17", 0),
                        "predicted_17_35": forecast.get("predicted_17_35", 0),
                        "predicted_35_plus": forecast.get("predicted_35_plus", 0),
                        "total": forecast.get("total_predicted", 0),
                        "confidence": forecast.get("confidence", 0),
                        "data_quality": forecast.get("data_quality", "unknown")
                    }
                    matrix_data.append(row)
        
        return pd.DataFrame(matrix_data)

# =============================================================================
# LLM RESPONSE GENERATOR
# =============================================================================

class LLMResponseGenerator:
    """
    Generates structured responses for LLM interpretation.
    
    Rules:
    - Never compute numbers
    - Never override confidence
    - Always cite source metric
    - Role-based filtering
    """
    
    ROLE_FILTERS = {
        "police": ["police_force_delta", "youth_density_index", "law_order_stress", "migration_rate"],
        "education": ["school_seats_needed", "dropout_risk_index", "education_budget_index"],
        "health": ["hospital_beds_delta", "doctor_gap", "maternity_load_index"],
        "budget": ["overall_budget_stress", "education_budget_index", "priority_sectors"],
        "skill": ["skill_training_demand", "migration_skill_loss", "youth_density_index"],
        "district_admin": ["priority_sectors", "overall_budget_stress", "trigger_metrics"],
        "state_govt": ["priority_sectors", "overall_budget_stress", "confidence"],
    }
    
    def generate_context(self, result: Dict, role: str = "district_admin") -> Dict:
        """
        Generate LLM-safe context for a specific role.
        
        LLM sees only processed data, never raw.
        """
        if "error" in result:
            return {"error": result["error"]}
        
        context = {
            "role": role,
            "district": result.get("district"),
            "model_version": MODEL_VERSION,
            "data_quality": result.get("data_quality", {}).get("overall_quality", "unknown"),
            "confidence_note": self._get_confidence_note(result),
        }
        
        # Filter based on role
        allowed_fields = self.ROLE_FILTERS.get(role, [])
        
        # Add forecasts
        if "forecasts" in result:
            context["forecasts"] = {}
            for horizon, forecast in result["forecasts"].items():
                context["forecasts"][horizon] = {
                    "year": forecast.get("forecast_year"),
                    "total_population": forecast.get("total_predicted"),
                    "confidence": forecast.get("confidence"),
                }
        
        # Add role-specific policy impacts
        if "policy_impacts" in result:
            context["policy_insights"] = {}
            for horizon, impact in result["policy_impacts"].items():
                filtered = {k: v for k, v in impact.items() if k in allowed_fields}
                filtered["horizon"] = horizon
                context["policy_insights"][horizon] = filtered
        
        return context
    
    def _get_confidence_note(self, result: Dict) -> str:
        """Generate human-readable confidence note"""
        quality = result.get("data_quality", {}).get("overall_quality", "medium")
        issues = result.get("data_quality", {}).get("issues", [])
        
        if quality == "high":
            return "High confidence projection based on complete data."
        elif quality == "medium":
            issue_text = ", ".join(issues[:2]) if issues else "minor data gaps"
            return f"Medium confidence projection. Note: {issue_text}."
        elif quality == "low":
            return "Low confidence projection. Significant data quality issues detected."
        else:
            return "Critical data quality issues. Use projections with extreme caution."
    
    def format_response_template(self, context: Dict, question: str = None) -> str:
        """
        Format response in the required template.
        
        [Context]
        [Forecast]
        [Confidence]
        [Action]
        """
        role = context.get("role", "district_admin")
        district = context.get("district", "Unknown")
        
        # Context section
        response = f"Context:\n"
        response += f"Analysis for {district} district. Role: {role.replace('_', ' ').title()}.\n\n"
        
        # Forecast section
        response += "Forecast:\n"
        if "forecasts" in context:
            for horizon, forecast in context["forecasts"].items():
                response += f"- {horizon}: Projected population {forecast.get('total_population', 'N/A'):,}\n"
        
        # Policy insights
        if "policy_insights" in context:
            response += "\nKey Insights:\n"
            for horizon, insights in context["policy_insights"].items():
                for key, value in insights.items():
                    if key != "horizon":
                        display_key = key.replace("_", " ").title()
                        response += f"- {display_key}: {value}\n"
        
        # Confidence section
        response += f"\nConfidence:\n{context.get('confidence_note', 'Confidence level not available.')}\n"
        
        # Action section
        response += "\nRecommended Action:\n"
        if "policy_insights" in context and "5Y" in context["policy_insights"]:
            priorities = context["policy_insights"]["5Y"].get("priority_sectors", [])
            if priorities:
                response += f"Priority focus on: {', '.join(priorities)}.\n"
            stress = context["policy_insights"]["5Y"].get("overall_budget_stress", "")
            if stress:
                response += f"Budget stress level: {stress}.\n"
        
        response += f"\nSource: {MODEL_VERSION}"
        
        return response

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'GovernanceIntelligenceEngine',
    'DataQualityEngine',
    'SignalExtractionEngine', 
    'TransitionForecastEngine',
    'PolicyMappingEngine',
    'DistrictComparisonEngine',
    'LLMResponseGenerator',
    'DistrictStateVector',
    'ForecastResult',
    'PolicyImpact',
    'DataQualityReport',
    'MODEL_VERSION',
    'TRANSITION_CONFIG',
    'POLICY_RATIOS'
]
