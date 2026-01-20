"""
Phase 1: Data Engineering & Neighbor Logic
==========================================
This script performs:
1. Data Merging - Combining all Aadhaar datasets
2. Spatial Neighbor Engineering - Using KNN to find geographic neighbors
3. Anomaly Metric Calculation - Z-Score based risk flagging
"""

import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors
import glob
import os
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from csv_utils import save_chunked_csv

# Set the working directory
BASE_DIR = Path(r"c:\Users\aarya\OneDrive\Desktop\coding\uidai_hackathon")

print("=" * 60)
print("PHASE 1: DATA ENGINEERING & NEIGHBOR LOGIC")
print("=" * 60)

# ============================================================
# TASK 1: DATA MERGING
# ============================================================
print("\n" + "=" * 60)
print("TASK 1: DATA MERGING")
print("=" * 60)

# Function to load and concatenate CSV files from a directory
def load_csv_files(pattern):
    """Load all CSV files matching the pattern and concatenate them."""
    files = glob.glob(pattern)
    print(f"  Found {len(files)} files matching pattern")
    dfs = []
    for f in files:
        print(f"    Loading: {os.path.basename(f)}")
        df = pd.read_csv(f)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)

# 1.1 Load Enrolment Data
print("\n[1.1] Loading Enrolment Data...")
enrolment_pattern = str(BASE_DIR / "api_data_aadhar_enrolment" / "api_data_aadhar_enrolment" / "*.csv")
enrolment_df = load_csv_files(enrolment_pattern)
print(f"  Enrolment records: {len(enrolment_df):,}")
print(f"  Columns: {list(enrolment_df.columns)}")

# 1.2 Load Demographic Data
print("\n[1.2] Loading Demographic Data...")
demographic_pattern = str(BASE_DIR / "api_data_aadhar_demographic" / "api_data_aadhar_demographic" / "*.csv")
demographic_df = load_csv_files(demographic_pattern)
print(f"  Demographic records: {len(demographic_df):,}")
print(f"  Columns: {list(demographic_df.columns)}")

# 1.3 Load Biometric Data
print("\n[1.3] Loading Biometric Data...")
biometric_pattern = str(BASE_DIR / "api_data_aadhar_biometric" / "api_data_aadhar_biometric" / "*.csv")
biometric_df = load_csv_files(biometric_pattern)
print(f"  Biometric records: {len(biometric_df):,}")
print(f"  Columns: {list(biometric_df.columns)}")

# 1.4 Load Pincode Lat/Long Data
print("\n[1.4] Loading Pincode Lat/Long Data...")
pincode_df = pd.read_csv(BASE_DIR / "pincode_lat_long.csv")
print(f"  Pincode records: {len(pincode_df):,}")
print(f"  Columns: {list(pincode_df.columns)}")

# 1.5 Standardize column names (lowercase, strip whitespace)
print("\n[1.5] Standardizing column names...")
for df in [enrolment_df, demographic_df, biometric_df, pincode_df]:
    df.columns = df.columns.str.strip().str.lower()

# 1.6 Merge the three Aadhaar datasets
print("\n[1.6] Merging Aadhaar datasets (enrolment + demographic + biometric)...")

# First, merge enrolment and demographic
master_df = pd.merge(
    enrolment_df,
    demographic_df,
    on=['date', 'state', 'district', 'pincode'],
    how='outer'
)
print(f"  After enrolment + demographic merge: {len(master_df):,} records")

# Then merge with biometric
master_df = pd.merge(
    master_df,
    biometric_df,
    on=['date', 'state', 'district', 'pincode'],
    how='outer'
)
print(f"  After adding biometric: {len(master_df):,} records")

# 1.7 Fill missing values with 0
print("\n[1.7] Filling missing values with 0...")
numeric_cols = ['age_0_5', 'age_5_17', 'age_18_greater', 
                'demo_age_5_17', 'demo_age_17_', 
                'bio_age_5_17', 'bio_age_17_']
for col in numeric_cols:
    if col in master_df.columns:
        master_df[col] = master_df[col].fillna(0)
print(f"  Filled NaN values in numeric columns")

# 1.8 Convert date to datetime
print("\n[1.8] Converting date to datetime...")
master_df['date'] = pd.to_datetime(master_df['date'], format='%d-%m-%Y', errors='coerce')
print(f"  Date range: {master_df['date'].min()} to {master_df['date'].max()}")

# 1.9 Create aggregated metrics for easier analysis
print("\n[1.9] Creating aggregated metrics...")
master_df['total_enrolment'] = master_df['age_0_5'] + master_df['age_5_17'] + master_df['age_18_greater']
master_df['total_demographic'] = master_df['demo_age_5_17'] + master_df['demo_age_17_']
master_df['total_biometric'] = master_df['bio_age_5_17'] + master_df['bio_age_17_']
print("  Created: total_enrolment, total_demographic, total_biometric")

# 1.10 Prepare pincode lat/long data
print("\n[1.10] Preparing pincode lat/long data...")
# Select relevant columns and handle duplicates
pincode_geo = pincode_df[['pincode', 'latitude', 'longitude', 'district', 'statename']].copy()

# Convert lat/long to numeric, handling 'NA' strings
pincode_geo['latitude'] = pd.to_numeric(pincode_geo['latitude'], errors='coerce')
pincode_geo['longitude'] = pd.to_numeric(pincode_geo['longitude'], errors='coerce')

# Drop rows with missing lat/long
pincode_geo = pincode_geo.dropna(subset=['latitude', 'longitude'])
print(f"  Pincodes with valid lat/long: {len(pincode_geo):,}")

# Keep unique pincodes (take first occurrence if duplicates)
pincode_geo = pincode_geo.drop_duplicates(subset='pincode', keep='first')
print(f"  Unique pincodes: {len(pincode_geo):,}")

# 1.11 Merge master dataframe with lat/long data
print("\n[1.11] Merging with lat/long data...")
master_df = pd.merge(
    master_df,
    pincode_geo[['pincode', 'latitude', 'longitude']],
    on='pincode',
    how='left'
)

# Drop rows where lat/long is missing
rows_before = len(master_df)
master_df = master_df.dropna(subset=['latitude', 'longitude'])
rows_after = len(master_df)
print(f"  Rows before: {rows_before:,}, After (with valid lat/long): {rows_after:,}")
print(f"  Dropped {rows_before - rows_after:,} rows without coordinates")

print("\n" + "-" * 60)
print(f"TASK 1 COMPLETE: Master DataFrame has {len(master_df):,} records")
print(f"Columns: {list(master_df.columns)}")
print("-" * 60)

# ============================================================
# TASK 2: SPATIAL NEIGHBOR ENGINEERING
# ============================================================
print("\n" + "=" * 60)
print("TASK 2: SPATIAL NEIGHBOR ENGINEERING")
print("=" * 60)

# 2.1 Get unique pincodes with their coordinates
print("\n[2.1] Building pincode coordinate lookup...")
pincode_coords = master_df[['pincode', 'latitude', 'longitude']].drop_duplicates(subset='pincode')
pincode_coords = pincode_coords.reset_index(drop=True)
print(f"  Unique pincodes in dataset: {len(pincode_coords):,}")

# 2.2 Build KNN model using BallTree (efficient for geographic coordinates)
print("\n[2.2] Building KNN model with BallTree...")
# Convert to radians for haversine distance (proper geographic distance)
coords_radians = np.radians(pincode_coords[['latitude', 'longitude']].values)

# Use BallTree with haversine metric for accurate geographic distances
knn = NearestNeighbors(n_neighbors=6, metric='haversine', algorithm='ball_tree')
knn.fit(coords_radians)
print("  KNN model built successfully (using haversine distance)")

# 2.3 Find 5 nearest neighbors for each pincode (excluding itself)
print("\n[2.3] Finding 5 nearest neighbors for each pincode...")
distances, indices = knn.kneighbors(coords_radians)

# Create a dictionary mapping pincode -> list of neighbor pincodes
neighbor_dict = {}
for i, pincode in enumerate(pincode_coords['pincode'].values):
    # indices[i][0] is the pincode itself, so take indices[i][1:6] for 5 neighbors
    neighbor_indices = indices[i][1:6]
    neighbor_pincodes = pincode_coords.iloc[neighbor_indices]['pincode'].values
    neighbor_dict[pincode] = neighbor_pincodes

print(f"  Neighbor mapping created for {len(neighbor_dict):,} pincodes")

# Show sample
sample_pincode = list(neighbor_dict.keys())[0]
print(f"  Sample - Pincode {sample_pincode} neighbors: {neighbor_dict[sample_pincode]}")

# 2.4 Calculate neighbor averages for each date-pincode combination
print("\n[2.4] Calculating neighbor averages (this may take a while)...")

# First, aggregate data by date-pincode to handle duplicates
print("  Aggregating data by date-pincode...")
agg_df = master_df.groupby(['date', 'pincode']).agg({
    'total_enrolment': 'sum',
    'total_demographic': 'sum',
    'total_biometric': 'sum'
}).reset_index()
print(f"  Unique date-pincode combinations: {len(agg_df):,}")

# Create a dictionary lookup for fast access
print("  Building date-pincode value lookup...")
date_pincode_lookup = {}
for _, row in agg_df.iterrows():
    key = (row['date'], row['pincode'])
    date_pincode_lookup[key] = {
        'total_enrolment': row['total_enrolment'],
        'total_demographic': row['total_demographic'],
        'total_biometric': row['total_biometric']
    }

# For efficiency, compute neighbor stats per unique (date, pincode) first
print("  Computing neighbor statistics per unique date-pincode...")
neighbor_stats = {}

unique_combinations = agg_df[['date', 'pincode']].values
total_unique = len(unique_combinations)
progress_step = max(1, total_unique // 10)

for i, (current_date, current_pincode) in enumerate(unique_combinations):
    if i % progress_step == 0:
        print(f"    Progress: {i/total_unique*100:.0f}%")
    
    if current_pincode not in neighbor_dict:
        continue
    
    neighbors = neighbor_dict[current_pincode]
    neighbor_values = {'enrolment': [], 'demographic': [], 'biometric': []}
    
    for neighbor_pincode in neighbors:
        key = (current_date, neighbor_pincode)
        if key in date_pincode_lookup:
            vals = date_pincode_lookup[key]
            neighbor_values['enrolment'].append(vals['total_enrolment'])
            neighbor_values['demographic'].append(vals['total_demographic'])
            neighbor_values['biometric'].append(vals['total_biometric'])
    
    stats = {}
    if neighbor_values['enrolment']:
        stats['neighbor_avg_enrolment'] = np.mean(neighbor_values['enrolment'])
        stats['neighbor_std_enrolment'] = np.std(neighbor_values['enrolment']) if len(neighbor_values['enrolment']) > 1 else 1.0
    else:
        stats['neighbor_avg_enrolment'] = 0.0
        stats['neighbor_std_enrolment'] = 1.0
    
    if neighbor_values['demographic']:
        stats['neighbor_avg_demographic'] = np.mean(neighbor_values['demographic'])
        stats['neighbor_std_demographic'] = np.std(neighbor_values['demographic']) if len(neighbor_values['demographic']) > 1 else 1.0
    else:
        stats['neighbor_avg_demographic'] = 0.0
        stats['neighbor_std_demographic'] = 1.0
    
    if neighbor_values['biometric']:
        stats['neighbor_avg_biometric'] = np.mean(neighbor_values['biometric'])
        stats['neighbor_std_biometric'] = np.std(neighbor_values['biometric']) if len(neighbor_values['biometric']) > 1 else 1.0
    else:
        stats['neighbor_avg_biometric'] = 0.0
        stats['neighbor_std_biometric'] = 1.0
    
    neighbor_stats[(current_date, current_pincode)] = stats

print("    Progress: 100%")

# Now map the neighbor stats back to the master dataframe
print("  Mapping neighbor stats to master dataframe...")
master_df['neighbor_avg_enrolment'] = master_df.apply(
    lambda row: neighbor_stats.get((row['date'], row['pincode']), {}).get('neighbor_avg_enrolment', 0.0), axis=1
)
master_df['neighbor_avg_demographic'] = master_df.apply(
    lambda row: neighbor_stats.get((row['date'], row['pincode']), {}).get('neighbor_avg_demographic', 0.0), axis=1
)
master_df['neighbor_avg_biometric'] = master_df.apply(
    lambda row: neighbor_stats.get((row['date'], row['pincode']), {}).get('neighbor_avg_biometric', 0.0), axis=1
)
master_df['neighbor_std_enrolment'] = master_df.apply(
    lambda row: neighbor_stats.get((row['date'], row['pincode']), {}).get('neighbor_std_enrolment', 1.0), axis=1
)
master_df['neighbor_std_demographic'] = master_df.apply(
    lambda row: neighbor_stats.get((row['date'], row['pincode']), {}).get('neighbor_std_demographic', 1.0), axis=1
)
master_df['neighbor_std_biometric'] = master_df.apply(
    lambda row: neighbor_stats.get((row['date'], row['pincode']), {}).get('neighbor_std_biometric', 1.0), axis=1
)
print("\n" + "-" * 60)
print("TASK 2 COMPLETE: Neighbor features calculated")
print("-" * 60)

# ============================================================
# TASK 3: ANOMALY METRIC CALCULATION
# ============================================================
print("\n" + "=" * 60)
print("TASK 3: ANOMALY METRIC CALCULATION")
print("=" * 60)

# 3.1 Calculate Z-Scores
print("\n[3.1] Calculating Z-Scores...")

# Avoid division by zero - replace 0 std with 1
master_df['neighbor_std_enrolment'] = master_df['neighbor_std_enrolment'].replace(0, 1)
master_df['neighbor_std_demographic'] = master_df['neighbor_std_demographic'].replace(0, 1)
master_df['neighbor_std_biometric'] = master_df['neighbor_std_biometric'].replace(0, 1)

# Calculate Z-Scores: (Current_Value - Neighbor_Avg) / Neighbor_Std_Dev
master_df['zscore_enrolment'] = (
    (master_df['total_enrolment'] - master_df['neighbor_avg_enrolment']) / 
    master_df['neighbor_std_enrolment']
)

master_df['zscore_demographic'] = (
    (master_df['total_demographic'] - master_df['neighbor_avg_demographic']) / 
    master_df['neighbor_std_demographic']
)

master_df['zscore_biometric'] = (
    (master_df['total_biometric'] - master_df['neighbor_avg_biometric']) / 
    master_df['neighbor_std_biometric']
)

# Fill any NaN/Inf values with 0
master_df['zscore_enrolment'] = master_df['zscore_enrolment'].replace([np.inf, -np.inf], 0).fillna(0)
master_df['zscore_demographic'] = master_df['zscore_demographic'].replace([np.inf, -np.inf], 0).fillna(0)
master_df['zscore_biometric'] = master_df['zscore_biometric'].replace([np.inf, -np.inf], 0).fillna(0)

print("  Z-Scores calculated for enrolment, demographic, and biometric")

# 3.2 Flag Risk_Influx
print("\n[3.2] Flagging Risk_Influx...")
# If enrolment is > 2.5 standard deviations higher than neighbors
ZSCORE_THRESHOLD = 2.5
master_df['Risk_Influx'] = (master_df['zscore_enrolment'] > ZSCORE_THRESHOLD).astype(int)
influx_count = master_df['Risk_Influx'].sum()
print(f"  Risk_Influx threshold: Z-Score > {ZSCORE_THRESHOLD}")
print(f"  Flagged as Risk_Influx: {influx_count:,} records ({influx_count/len(master_df)*100:.2f}%)")

# 3.3 Flag Risk_Ghost_Population
print("\n[3.3] Flagging Risk_Ghost_Population...")
# If biometric updates are abnormally low while demographic updates are high
# Logic: High demographic (Z > 1.5) AND Low biometric (Z < -1.5)
# This indicates demographic changes without corresponding biometric verification

master_df['Risk_Ghost_Population'] = (
    (master_df['zscore_demographic'] > 1.5) & 
    (master_df['zscore_biometric'] < -1.5)
).astype(int)

ghost_count = master_df['Risk_Ghost_Population'].sum()
print(f"  Risk_Ghost_Population criteria:")
print(f"    - High demographic updates (Z-Score > 1.5)")
print(f"    - Low biometric updates (Z-Score < -1.5)")
print(f"  Flagged as Risk_Ghost_Population: {ghost_count:,} records ({ghost_count/len(master_df)*100:.2f}%)")

# 3.4 Add combined risk score
print("\n[3.4] Creating combined risk indicators...")
master_df['Risk_Any'] = ((master_df['Risk_Influx'] == 1) | (master_df['Risk_Ghost_Population'] == 1)).astype(int)
master_df['Risk_Score'] = (
    abs(master_df['zscore_enrolment']) + 
    abs(master_df['zscore_demographic']) + 
    abs(master_df['zscore_biometric'])
) / 3

any_risk_count = master_df['Risk_Any'].sum()
print(f"  Records with any risk flag: {any_risk_count:,} ({any_risk_count/len(master_df)*100:.2f}%)")

print("\n" + "-" * 60)
print("TASK 3 COMPLETE: Anomaly metrics calculated")
print("-" * 60)

# ============================================================
# SAVE PROCESSED DATA
# ============================================================
print("\n" + "=" * 60)
print("SAVING PROCESSED DATA")
print("=" * 60)

# Save as chunks for GitHub compatibility (files over 100MB)
save_chunked_csv(master_df, "processed_aadhaar_risk_data")
print(f"\nSaved as chunks in chunked_data/")
print(f"Total records: {len(master_df):,}")
print(f"Total columns: {len(master_df.columns)}")

# Print final summary
print("\n" + "=" * 60)
print("FINAL SUMMARY")
print("=" * 60)

print("\nColumn List:")
for i, col in enumerate(master_df.columns):
    print(f"  {i+1}. {col}")

print("\nRisk Summary:")
print(f"  - Total Records: {len(master_df):,}")
print(f"  - Risk_Influx: {master_df['Risk_Influx'].sum():,} ({master_df['Risk_Influx'].mean()*100:.2f}%)")
print(f"  - Risk_Ghost_Population: {master_df['Risk_Ghost_Population'].sum():,} ({master_df['Risk_Ghost_Population'].mean()*100:.2f}%)")
print(f"  - Any Risk Flag: {master_df['Risk_Any'].sum():,} ({master_df['Risk_Any'].mean()*100:.2f}%)")

print("\nData Sample (first 5 rows with risk flags):")
risk_sample = master_df[master_df['Risk_Any'] == 1].head()
if len(risk_sample) > 0:
    print(risk_sample[['date', 'pincode', 'state', 'total_enrolment', 'total_demographic', 
                       'total_biometric', 'zscore_enrolment', 'Risk_Influx', 'Risk_Ghost_Population']].to_string())
else:
    print("  No risk flags found in sample")

print("\n" + "=" * 60)
print("PHASE 1 COMPLETE!")
print("=" * 60)
