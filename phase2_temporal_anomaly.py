"""
Phase 2: Temporal Anomaly Detection (Time-Series Analysis)
==========================================================
This script performs:
1. Trend Analysis - 7-day rolling averages per pincode
2. Spike Detection - Identify sudden spikes (>300% of rolling avg)
3. Severity Scoring - Combined Risk_Score (0-100)
4. Export final dataset for dashboard
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from csv_utils import load_chunked_csv, save_chunked_csv

# Set the working directory
BASE_DIR = Path(r"c:\Users\aarya\OneDrive\Desktop\coding\uidai_hackathon")

print("=" * 60)
print("PHASE 2: TEMPORAL ANOMALY DETECTION")
print("=" * 60)

# ============================================================
# LOAD PROCESSED DATA
# ============================================================
print("\n[1] Loading processed data from Phase 1...")
print("    (This may take a moment for large files...)")

# Load the data using chunked CSV loader
try:
    df = load_chunked_csv("processed_aadhaar_risk_data", low_memory=False)
    print(f"    Loaded {len(df):,} records successfully")
except Exception as e:
    print(f"    Error loading data: {e}")
    raise

# Convert date column to datetime
print("\n[2] Converting date column to datetime...")
df['date'] = pd.to_datetime(df['date'], errors='coerce')
print(f"    Date range: {df['date'].min()} to {df['date'].max()}")

# Ensure numeric columns
numeric_cols = ['total_enrolment', 'total_demographic', 'total_biometric', 
                'Risk_Influx', 'Risk_Ghost_Population']
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

print(f"    Unique pincodes: {df['pincode'].nunique():,}")
print(f"    Unique dates: {df['date'].nunique():,}")

# ============================================================
# TASK 1: TREND ANALYSIS - 7-Day Rolling Averages
# ============================================================
print("\n" + "=" * 60)
print("TASK 1: TREND ANALYSIS - 7-Day Rolling Averages")
print("=" * 60)

# First, aggregate by date and pincode to get daily totals
print("\n[1.1] Aggregating daily totals per pincode...")
daily_agg = df.groupby(['pincode', 'date']).agg({
    'total_enrolment': 'sum',
    'total_demographic': 'sum',
    'total_biometric': 'sum',
    'latitude': 'first',
    'longitude': 'first',
    'state': 'first',
    'district': 'first'
}).reset_index()

print(f"    Daily aggregated records: {len(daily_agg):,}")

# Sort by pincode and date for rolling calculations
daily_agg = daily_agg.sort_values(['pincode', 'date']).reset_index(drop=True)

# Calculate 7-day rolling averages per pincode
print("\n[1.2] Calculating 7-day rolling averages per pincode...")

def calculate_rolling_stats(group):
    """Calculate rolling statistics for a pincode group."""
    group = group.sort_values('date')
    
    # 7-day rolling average (min_periods=1 to handle edge cases)
    group['rolling_7d_enrolment'] = group['total_enrolment'].rolling(
        window=7, min_periods=1
    ).mean()
    
    group['rolling_7d_demographic'] = group['total_demographic'].rolling(
        window=7, min_periods=1
    ).mean()
    
    group['rolling_7d_biometric'] = group['total_biometric'].rolling(
        window=7, min_periods=1
    ).mean()
    
    return group

# Apply rolling calculation per pincode
print("    Processing pincodes (this may take a while)...")
unique_pincodes = daily_agg['pincode'].unique()
total_pincodes = len(unique_pincodes)
progress_step = max(1, total_pincodes // 10)

processed_groups = []
for i, pincode in enumerate(unique_pincodes):
    if i % progress_step == 0:
        print(f"      Progress: {i/total_pincodes*100:.0f}%")
    
    group = daily_agg[daily_agg['pincode'] == pincode].copy()
    processed_group = calculate_rolling_stats(group)
    processed_groups.append(processed_group)

print("      Progress: 100%")

daily_agg = pd.concat(processed_groups, ignore_index=True)
print(f"    Rolling averages calculated for {total_pincodes:,} pincodes")

# ============================================================
# TASK 2: SPIKE DETECTION
# ============================================================
print("\n" + "=" * 60)
print("TASK 2: SPIKE DETECTION (>300% of 7-day rolling avg)")
print("=" * 60)

# Detect spikes where daily value > 300% (3x) of rolling average
SPIKE_THRESHOLD = 3.0  # 300%

print("\n[2.1] Detecting enrollment spikes...")
# Avoid division by zero - use a small epsilon
epsilon = 0.1
daily_agg['enrolment_spike_ratio'] = daily_agg['total_enrolment'] / (
    daily_agg['rolling_7d_enrolment'] + epsilon
)
daily_agg['Spike_Enrolment'] = (daily_agg['enrolment_spike_ratio'] > SPIKE_THRESHOLD).astype(int)
enrolment_spikes = daily_agg['Spike_Enrolment'].sum()
print(f"    Enrollment spikes detected: {enrolment_spikes:,}")

print("\n[2.2] Detecting demographic update spikes...")
daily_agg['demographic_spike_ratio'] = daily_agg['total_demographic'] / (
    daily_agg['rolling_7d_demographic'] + epsilon
)
daily_agg['Spike_Demographic'] = (daily_agg['demographic_spike_ratio'] > SPIKE_THRESHOLD).astype(int)
demographic_spikes = daily_agg['Spike_Demographic'].sum()
print(f"    Demographic spikes detected: {demographic_spikes:,}")

print("\n[2.3] Creating combined Sudden_Spike_Anomaly flag...")
# Either enrollment OR demographic spike triggers the anomaly
daily_agg['Sudden_Spike_Anomaly'] = (
    (daily_agg['Spike_Enrolment'] == 1) | 
    (daily_agg['Spike_Demographic'] == 1)
).astype(int)
spike_anomalies = daily_agg['Sudden_Spike_Anomaly'].sum()
print(f"    Total Sudden_Spike_Anomaly records: {spike_anomalies:,}")

# ============================================================
# TASK 3: SEVERITY SCORING (0-100)
# ============================================================
print("\n" + "=" * 60)
print("TASK 3: SEVERITY SCORING (Risk_Score 0-100)")
print("=" * 60)

# Need to merge back the spatial risk flags from original data
print("\n[3.1] Merging spatial risk flags from Phase 1...")

# Get spatial risk flags per date-pincode from original df
spatial_risks = df.groupby(['date', 'pincode']).agg({
    'Risk_Influx': 'max',
    'Risk_Ghost_Population': 'max'
}).reset_index()

daily_agg = pd.merge(
    daily_agg,
    spatial_risks,
    on=['date', 'pincode'],
    how='left'
)

# Fill NaN with 0
daily_agg['Risk_Influx'] = daily_agg['Risk_Influx'].fillna(0).astype(int)
daily_agg['Risk_Ghost_Population'] = daily_agg['Risk_Ghost_Population'].fillna(0).astype(int)

print("\n[3.2] Calculating Risk_Score (0-100)...")

# Initialize Risk_Score at 0
daily_agg['Risk_Score'] = 0

# +20 points if Risk_Influx is True (Spatial anomaly)
daily_agg['Risk_Score'] += daily_agg['Risk_Influx'] * 20
print("    +20 points for Risk_Influx (Spatial anomaly)")

# +30 points if Sudden_Spike_Anomaly is True (Temporal anomaly)
daily_agg['Risk_Score'] += daily_agg['Sudden_Spike_Anomaly'] * 30
print("    +30 points for Sudden_Spike_Anomaly (Temporal anomaly)")

# +50 points if demographic updates > 500 in a single day (Mass migration alert)
MASS_MIGRATION_THRESHOLD = 500
daily_agg['Mass_Migration_Alert'] = (daily_agg['total_demographic'] > MASS_MIGRATION_THRESHOLD).astype(int)
daily_agg['Risk_Score'] += daily_agg['Mass_Migration_Alert'] * 50
print(f"    +50 points for demographic > {MASS_MIGRATION_THRESHOLD} (Mass migration)")

# +15 bonus for Ghost Population (severe fraud indicator)
daily_agg['Risk_Score'] += daily_agg['Risk_Ghost_Population'] * 15
print("    +15 points for Risk_Ghost_Population (Fraud indicator)")

# Cap at 100
daily_agg['Risk_Score'] = daily_agg['Risk_Score'].clip(0, 100)

print("\n[3.3] Risk Score Distribution:")
print(f"    Score = 0:     {(daily_agg['Risk_Score'] == 0).sum():,} records")
print(f"    Score 1-25:    {((daily_agg['Risk_Score'] > 0) & (daily_agg['Risk_Score'] <= 25)).sum():,} records")
print(f"    Score 26-50:   {((daily_agg['Risk_Score'] > 25) & (daily_agg['Risk_Score'] <= 50)).sum():,} records")
print(f"    Score 51-75:   {((daily_agg['Risk_Score'] > 50) & (daily_agg['Risk_Score'] <= 75)).sum():,} records")
print(f"    Score 76-100:  {(daily_agg['Risk_Score'] > 75).sum():,} records")

# Create risk categories for easier visualization
daily_agg['Risk_Category'] = pd.cut(
    daily_agg['Risk_Score'],
    bins=[-1, 0, 25, 50, 75, 100],
    labels=['No Risk', 'Low', 'Medium', 'High', 'Critical']
)

print("\n    Risk Categories:")
print(daily_agg['Risk_Category'].value_counts().to_string())

# ============================================================
# EXPORT FINAL DATASET
# ============================================================
print("\n" + "=" * 60)
print("EXPORTING FINAL DATASET")
print("=" * 60)

# Select and order columns for dashboard
dashboard_columns = [
    'date', 'pincode', 'state', 'district', 'latitude', 'longitude',
    'total_enrolment', 'total_demographic', 'total_biometric',
    'rolling_7d_enrolment', 'rolling_7d_demographic', 'rolling_7d_biometric',
    'enrolment_spike_ratio', 'demographic_spike_ratio',
    'Spike_Enrolment', 'Spike_Demographic', 'Sudden_Spike_Anomaly',
    'Risk_Influx', 'Risk_Ghost_Population', 'Mass_Migration_Alert',
    'Risk_Score', 'Risk_Category'
]

final_df = daily_agg[dashboard_columns].copy()

# Sort by Risk_Score descending, then by date
final_df = final_df.sort_values(['Risk_Score', 'date'], ascending=[False, True])

# Save main output as chunks (for GitHub compatibility)
save_chunked_csv(final_df, "final_aadhaar_risk_dashboard_data")
print(f"\n[1] Main dataset saved as chunks")
print(f"    Records: {len(final_df):,}")

# Also save a high-risk subset for quick analysis
high_risk_df = final_df[final_df['Risk_Score'] > 0].copy()
high_risk_file = BASE_DIR / "high_risk_pincodes.csv"
high_risk_df.to_csv(high_risk_file, index=False)
print(f"\n[2] High-risk subset saved: {high_risk_file}")
print(f"    High-risk records: {len(high_risk_df):,}")

# Save summary statistics per pincode (for map visualization)
print("\n[3] Creating pincode summary for map visualization...")
pincode_summary = final_df.groupby('pincode').agg({
    'state': 'first',
    'district': 'first',
    'latitude': 'first',
    'longitude': 'first',
    'total_enrolment': 'sum',
    'total_demographic': 'sum',
    'total_biometric': 'sum',
    'Sudden_Spike_Anomaly': 'sum',
    'Risk_Influx': 'max',
    'Risk_Ghost_Population': 'max',
    'Mass_Migration_Alert': 'sum',
    'Risk_Score': 'max'
}).reset_index()

pincode_summary.columns = [
    'pincode', 'state', 'district', 'latitude', 'longitude',
    'total_enrolment', 'total_demographic', 'total_biometric',
    'spike_count', 'ever_influx_risk', 'ever_ghost_risk', 
    'mass_migration_days', 'max_risk_score'
]

# Add overall risk level per pincode
pincode_summary['pincode_risk_level'] = pd.cut(
    pincode_summary['max_risk_score'],
    bins=[-1, 0, 25, 50, 75, 100],
    labels=['No Risk', 'Low', 'Medium', 'High', 'Critical']
)

pincode_summary_file = BASE_DIR / "pincode_risk_summary.csv"
pincode_summary.to_csv(pincode_summary_file, index=False)
print(f"    Pincode summary saved: {pincode_summary_file}")
print(f"    Unique pincodes: {len(pincode_summary):,}")

# ============================================================
# FINAL SUMMARY
# ============================================================
print("\n" + "=" * 60)
print("PHASE 2 COMPLETE - FINAL SUMMARY")
print("=" * 60)

print("\n📊 DATA OVERVIEW:")
print(f"    Total daily records: {len(final_df):,}")
print(f"    Unique pincodes: {final_df['pincode'].nunique():,}")
print(f"    Date range: {final_df['date'].min()} to {final_df['date'].max()}")

print("\n🚨 ANOMALY DETECTION RESULTS:")
print(f"    Sudden Spike Anomalies: {final_df['Sudden_Spike_Anomaly'].sum():,}")
print(f"    Risk Influx (Spatial): {final_df['Risk_Influx'].sum():,}")
print(f"    Ghost Population Risks: {final_df['Risk_Ghost_Population'].sum():,}")
print(f"    Mass Migration Alerts: {final_df['Mass_Migration_Alert'].sum():,}")

print("\n📈 RISK SCORE SUMMARY:")
print(f"    Mean Risk Score: {final_df['Risk_Score'].mean():.2f}")
print(f"    Max Risk Score: {final_df['Risk_Score'].max():.0f}")
print(f"    Records with any risk: {(final_df['Risk_Score'] > 0).sum():,} ({(final_df['Risk_Score'] > 0).mean()*100:.2f}%)")

print("\n📁 OUTPUT FILES:")
print(f"    1. {output_file.name} - Full dataset for dashboard")
print(f"    2. {high_risk_file.name} - High-risk records only")
print(f"    3. {pincode_summary_file.name} - Pincode-level summary for maps")

print("\n" + "=" * 60)
print("READY FOR DASHBOARD VISUALIZATION! 🚀")
print("=" * 60)

# Show top 10 highest risk records
print("\n🔴 TOP 10 HIGHEST RISK RECORDS:")
top_risk = final_df.nlargest(10, 'Risk_Score')[
    ['date', 'pincode', 'state', 'district', 'total_demographic', 'Risk_Score', 'Risk_Category']
]
print(top_risk.to_string(index=False))
