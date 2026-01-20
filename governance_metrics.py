"""
Governance Intelligence - Multi-Sector Metric Calculation
==========================================================
Calculates sector-specific metrics for:
1. Education (School Dropout Risk)
2. Civil Supplies/Ration (Migrant Hunger Score)
3. Rural Development (Village Hollow-Out Rate)
4. Election Commission (Electoral Discrepancy Index)
5. Labor & Employment (Skill Gap Migration Flow)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
import warnings
warnings.filterwarnings('ignore')

from csv_utils import load_chunked_csv, save_chunked_csv

BASE_DIR = Path(r"c:\Users\aarya\OneDrive\Desktop\coding\uidai_hackathon")

print("=" * 70)
print("GOVERNANCE INTELLIGENCE - MULTI-SECTOR ANALYSIS")
print("=" * 70)

# ============================================================
# LOAD DATA
# ============================================================
print("\n[1] Loading processed data...")

# Load the final dashboard data (has daily aggregations)
df = load_chunked_csv("final_aadhaar_risk_dashboard_data", low_memory=False)
df['date'] = pd.to_datetime(df['date'])
print(f"    Loaded {len(df):,} records")

# Load original processed data for age-specific columns
original_df = load_chunked_csv("processed_aadhaar_risk_data", low_memory=False)
original_df['date'] = pd.to_datetime(original_df['date'])
print(f"    Loaded original data: {len(original_df):,} records")

# Aggregate age-specific data by date and pincode
print("\n[2] Aggregating age-specific metrics...")
age_agg = original_df.groupby(['date', 'pincode']).agg({
    'age_0_5': 'sum',
    'age_5_17': 'sum',
    'age_18_greater': 'sum',
    'demo_age_5_17': 'sum',
    'demo_age_17_': 'sum',
    'bio_age_5_17': 'sum',
    'bio_age_17_': 'sum',
    'state': 'first',
    'district': 'first',
    'latitude': 'first',
    'longitude': 'first'
}).reset_index()

print(f"    Aggregated to {len(age_agg):,} date-pincode records")

# Merge with dashboard data to get risk flags
merged_df = pd.merge(
    age_agg,
    df[['date', 'pincode', 'Risk_Score', 'Risk_Influx', 'Risk_Ghost_Population', 
        'Sudden_Spike_Anomaly', 'Mass_Migration_Alert', 'rolling_7d_demographic']],
    on=['date', 'pincode'],
    how='left'
)

# Fill NaN values
merged_df = merged_df.fillna(0)
print(f"    Merged dataset: {len(merged_df):,} records")

# ============================================================
# SECTOR 1: EDUCATION (School Dropout Risk Index)
# ============================================================
print("\n" + "=" * 70)
print("SECTOR 1: EDUCATION - School Dropout Risk Index")
print("=" * 70)

"""
Logic: Compare enrolled children (age_0_5 + age_5_17) against biometric updates
for school-age children (bio_age_5_17). 
If many children enrolled but few biometric updates -> Ghost Children zones
"""

# Calculate total children enrolled
merged_df['children_enrolled'] = merged_df['age_0_5'] + merged_df['age_5_17']

# Calculate School Dropout Risk Index
# High enrollment + Low biometric verification = High risk
epsilon = 1  # Avoid division by zero

merged_df['bio_to_enroll_ratio'] = merged_df['bio_age_5_17'] / (merged_df['children_enrolled'] + epsilon)

# Invert: Low ratio = High dropout risk
# Normalize to 0-100 scale
merged_df['School_Dropout_Risk_Index'] = 100 - (merged_df['bio_to_enroll_ratio'].clip(0, 1) * 100)

# Also factor in demographic updates for children (address changes = migration)
merged_df['child_migration_factor'] = merged_df['demo_age_5_17'] / (merged_df['children_enrolled'] + epsilon)
merged_df['School_Dropout_Risk_Index'] = (
    merged_df['School_Dropout_Risk_Index'] * 0.7 + 
    merged_df['child_migration_factor'].clip(0, 1) * 100 * 0.3
).clip(0, 100)

print(f"    Mean School Dropout Risk: {merged_df['School_Dropout_Risk_Index'].mean():.2f}")
print(f"    High Risk (>70): {(merged_df['School_Dropout_Risk_Index'] > 70).sum():,} records")

# ============================================================
# SECTOR 2: CIVIL SUPPLIES (Migrant Hunger Score)
# ============================================================
print("\n" + "=" * 70)
print("SECTOR 2: CIVIL SUPPLIES - Migrant Hunger Score")
print("=" * 70)

"""
Logic: High adult demographic updates (migration in) + Low biometric auth
indicates migrants who may not have access to local ration services
"""

# High demographic changes for adults = incoming migrants
merged_df['adult_migration_volume'] = merged_df['demo_age_17_']

# Calculate percentile-based scoring
adult_migration_pctl = merged_df['adult_migration_volume'].rank(pct=True) * 100

# Migrant Hunger Score: High migration + spikes + mass migration alerts
merged_df['Migrant_Hunger_Score'] = (
    adult_migration_pctl * 0.5 +
    merged_df['Mass_Migration_Alert'] * 30 +
    merged_df['Sudden_Spike_Anomaly'] * 20
).clip(0, 100)

print(f"    Mean Migrant Hunger Score: {merged_df['Migrant_Hunger_Score'].mean():.2f}")
print(f"    Critical (>80): {(merged_df['Migrant_Hunger_Score'] > 80).sum():,} records")

# ============================================================
# SECTOR 3: RURAL DEVELOPMENT (Village Hollow-Out Rate)
# ============================================================
print("\n" + "=" * 70)
print("SECTOR 3: RURAL DEVELOPMENT - Village Hollow-Out Rate")
print("=" * 70)

"""
Logic: Ratio of demographic out-migration (address changes) vs 
new enrollments. If people leaving > people staying/coming = hollowing out
"""

# Total demographic updates = address changes (proxy for migration)
merged_df['total_address_changes'] = merged_df['demo_age_5_17'] + merged_df['demo_age_17_']

# New enrollments = new residents
merged_df['new_residents'] = merged_df['age_0_5'] + merged_df['age_5_17'] + merged_df['age_18_greater']

# Hollow-out ratio: High address changes relative to new enrollments
merged_df['hollow_out_ratio'] = merged_df['total_address_changes'] / (merged_df['new_residents'] + epsilon)

# Normalize to 0-100
merged_df['Village_Hollow_Out_Rate'] = (merged_df['hollow_out_ratio'].rank(pct=True) * 100).clip(0, 100)

# Boost score for areas with ghost population risk (only elderly remaining)
merged_df['Village_Hollow_Out_Rate'] = (
    merged_df['Village_Hollow_Out_Rate'] * 0.8 +
    merged_df['Risk_Ghost_Population'] * 20
).clip(0, 100)

print(f"    Mean Hollow-Out Rate: {merged_df['Village_Hollow_Out_Rate'].mean():.2f}")
print(f"    Severe Hollowing (>75): {(merged_df['Village_Hollow_Out_Rate'] > 75).sum():,} records")

# ============================================================
# SECTOR 4: ELECTION COMMISSION (Electoral Discrepancy Index)
# ============================================================
print("\n" + "=" * 70)
print("SECTOR 4: ELECTION COMMISSION - Electoral Discrepancy Index")
print("=" * 70)

"""
Logic: Sudden adult enrollment spikes may indicate 'ghost citizens'
Flag areas with abnormal new adult Aadhaar registrations
"""

# New adult enrollments
merged_df['new_adult_enrolments'] = merged_df['age_18_greater']

# Calculate rolling average for comparison
# Use existing spike detection - if adult enrollments spike, flag it
merged_df['adult_enroll_pctl'] = merged_df['new_adult_enrolments'].rank(pct=True)

# Electoral Discrepancy Index
merged_df['Electoral_Discrepancy_Index'] = (
    merged_df['adult_enroll_pctl'] * 50 +  # High adult enrollment
    merged_df['Risk_Influx'] * 30 +         # Spatial anomaly
    merged_df['Sudden_Spike_Anomaly'] * 20  # Temporal spike
).clip(0, 100)

print(f"    Mean Electoral Discrepancy: {merged_df['Electoral_Discrepancy_Index'].mean():.2f}")
print(f"    High Alert (>70): {(merged_df['Electoral_Discrepancy_Index'] > 70).sum():,} records")

# ============================================================
# SECTOR 5: LABOR & EMPLOYMENT (Skill Gap Migration Flow)
# ============================================================
print("\n" + "=" * 70)
print("SECTOR 5: LABOR & EMPLOYMENT - Skill Gap Migration Flow")
print("=" * 70)

"""
Logic: Biometric updates for adults indicate manual labor/employment
High biometric activity + high demographic changes = labor migration
"""

# Adult biometric updates (proxy for working population)
merged_df['labor_activity'] = merged_df['bio_age_17_']

# Migration component
merged_df['labor_migration'] = merged_df['demo_age_17_']

# Skill Gap Migration Flow Score
labor_activity_pctl = merged_df['labor_activity'].rank(pct=True)
labor_migration_pctl = merged_df['labor_migration'].rank(pct=True)

merged_df['Skill_Gap_Migration_Flow'] = (
    labor_migration_pctl * 40 +          # Migration volume
    labor_activity_pctl * 30 +           # Labor activity  
    merged_df['Mass_Migration_Alert'] * 30  # Mass movement
).clip(0, 100)

print(f"    Mean Skill Gap Flow: {merged_df['Skill_Gap_Migration_Flow'].mean():.2f}")
print(f"    High Movement (>70): {(merged_df['Skill_Gap_Migration_Flow'] > 70).sum():,} records")

# ============================================================
# CREATE COMPOSITE GOVERNANCE SCORE
# ============================================================
print("\n" + "=" * 70)
print("COMPOSITE GOVERNANCE INTELLIGENCE SCORE")
print("=" * 70)

# Weighted composite of all sectors
merged_df['Governance_Risk_Score'] = (
    merged_df['School_Dropout_Risk_Index'] * 0.20 +
    merged_df['Migrant_Hunger_Score'] * 0.20 +
    merged_df['Village_Hollow_Out_Rate'] * 0.15 +
    merged_df['Electoral_Discrepancy_Index'] * 0.25 +
    merged_df['Skill_Gap_Migration_Flow'] * 0.20
).round(2)

# Risk categorization
merged_df['Governance_Risk_Level'] = pd.cut(
    merged_df['Governance_Risk_Score'],
    bins=[-1, 20, 40, 60, 80, 100],
    labels=['Safe', 'Low', 'Medium', 'High', 'Critical']
)

print(f"    Mean Governance Risk: {merged_df['Governance_Risk_Score'].mean():.2f}")
print("\n    Risk Level Distribution:")
print(merged_df['Governance_Risk_Level'].value_counts().to_string())

# ============================================================
# IDENTIFY TOP PRIORITY AREAS PER SECTOR
# ============================================================
print("\n" + "=" * 70)
print("TOP PRIORITY AREAS BY SECTOR")
print("=" * 70)

# Aggregate to pincode level for summary
pincode_summary = merged_df.groupby('pincode').agg({
    'state': 'first',
    'district': 'first',
    'latitude': 'first',
    'longitude': 'first',
    'School_Dropout_Risk_Index': 'mean',
    'Migrant_Hunger_Score': 'mean',
    'Village_Hollow_Out_Rate': 'mean',
    'Electoral_Discrepancy_Index': 'mean',
    'Skill_Gap_Migration_Flow': 'mean',
    'Governance_Risk_Score': 'mean',
    'Risk_Score': 'max',
    'children_enrolled': 'sum',
    'adult_migration_volume': 'sum',
    'labor_activity': 'sum'
}).reset_index()

# Determine primary concern for each pincode
def get_primary_sector(row):
    scores = {
        'Education': row['School_Dropout_Risk_Index'],
        'Ration/Hunger': row['Migrant_Hunger_Score'],
        'Rural_Hollowing': row['Village_Hollow_Out_Rate'],
        'Electoral': row['Electoral_Discrepancy_Index'],
        'Labor': row['Skill_Gap_Migration_Flow']
    }
    return max(scores, key=scores.get)

pincode_summary['Primary_Sector_Concern'] = pincode_summary.apply(get_primary_sector, axis=1)

print("\n    Primary Sector Concern Distribution:")
print(pincode_summary['Primary_Sector_Concern'].value_counts().to_string())

# ============================================================
# SAVE OUTPUTS
# ============================================================
print("\n" + "=" * 70)
print("SAVING GOVERNANCE INTELLIGENCE DATA")
print("=" * 70)

# 1. Full daily dataset (save as chunks to stay under GitHub's 100MB limit)
# Select key columns for output
output_columns = [
    'date', 'pincode', 'state', 'district', 'latitude', 'longitude',
    'age_0_5', 'age_5_17', 'age_18_greater',
    'demo_age_5_17', 'demo_age_17_', 'bio_age_5_17', 'bio_age_17_',
    'children_enrolled', 'adult_migration_volume', 'labor_activity',
    'School_Dropout_Risk_Index', 'Migrant_Hunger_Score', 
    'Village_Hollow_Out_Rate', 'Electoral_Discrepancy_Index',
    'Skill_Gap_Migration_Flow', 'Governance_Risk_Score', 'Governance_Risk_Level',
    'Risk_Score', 'Risk_Influx', 'Risk_Ghost_Population', 
    'Sudden_Spike_Anomaly', 'Mass_Migration_Alert'
]
# Save as chunks for GitHub compatibility
save_chunked_csv(merged_df[output_columns], "governance_intelligence_master")
print(f"\n[1] Master dataset saved as chunks")
print(f"    Records: {len(merged_df):,}")

# 2. Pincode summary for API
summary_file = BASE_DIR / "governance_pincode_summary.csv"
pincode_summary.to_csv(summary_file, index=False)
print(f"\n[2] Pincode summary saved: {summary_file.name}")
print(f"    Unique pincodes: {len(pincode_summary):,}")

# 3. High-priority alerts (Risk > 60)
alerts_df = merged_df[merged_df['Governance_Risk_Score'] > 60].copy()
alerts_file = BASE_DIR / "governance_alerts.csv"
alerts_df[output_columns].to_csv(alerts_file, index=False)
print(f"\n[3] High-priority alerts saved: {alerts_file.name}")
print(f"    Alert records: {len(alerts_df):,}")

# 4. Sector-wise top 20 priorities
print("\n[4] Saving sector-wise priority lists...")

sectors = {
    'education_priorities': 'School_Dropout_Risk_Index',
    'hunger_priorities': 'Migrant_Hunger_Score',
    'rural_priorities': 'Village_Hollow_Out_Rate',
    'electoral_priorities': 'Electoral_Discrepancy_Index',
    'labor_priorities': 'Skill_Gap_Migration_Flow'
}

for filename, metric in sectors.items():
    top_df = pincode_summary.nlargest(50, metric)[
        ['pincode', 'state', 'district', 'latitude', 'longitude', metric, 'Governance_Risk_Score']
    ]
    top_df.to_csv(BASE_DIR / f"{filename}.csv", index=False)
    print(f"    Saved: {filename}.csv")

# ============================================================
# FINAL SUMMARY
# ============================================================
print("\n" + "=" * 70)
print("GOVERNANCE INTELLIGENCE - COMPLETE")
print("=" * 70)

print("\n📊 SECTOR ANALYSIS SUMMARY:")
print(f"    📚 Education Risk Areas: {(pincode_summary['School_Dropout_Risk_Index'] > 70).sum():,} pincodes")
print(f"    🍚 Hunger Risk Areas: {(pincode_summary['Migrant_Hunger_Score'] > 70).sum():,} pincodes")
print(f"    🏘️ Hollowing Villages: {(pincode_summary['Village_Hollow_Out_Rate'] > 70).sum():,} pincodes")
print(f"    🗳️ Electoral Anomalies: {(pincode_summary['Electoral_Discrepancy_Index'] > 70).sum():,} pincodes")
print(f"    👷 Labor Migration Hotspots: {(pincode_summary['Skill_Gap_Migration_Flow'] > 70).sum():,} pincodes")

print("\n🎯 TOP 10 CRITICAL GOVERNANCE AREAS:")
top_critical = pincode_summary.nlargest(10, 'Governance_Risk_Score')[
    ['pincode', 'state', 'district', 'Governance_Risk_Score', 'Primary_Sector_Concern']
]
print(top_critical.to_string(index=False))

print("\n✅ All governance metrics calculated and saved!")
print("=" * 70)
