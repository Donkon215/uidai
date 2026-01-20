"""
High-Resolution Infographics Generator
======================================
Creates presentation-ready visuals for the Pulse of Bharat project.
Uses seaborn and matplotlib with a professional government color palette.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter
import warnings
warnings.filterwarnings('ignore')

from csv_utils import load_chunked_csv

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(r"c:\Users\aarya\OneDrive\Desktop\coding\uidai_hackathon")
OUTPUT_DIR = BASE_DIR / "infographics"
OUTPUT_DIR.mkdir(exist_ok=True)

# Professional Government Color Palette
COLORS = {
    'navy': '#1a365d',
    'navy_light': '#2c5282',
    'alert_red': '#c53030',
    'warning_orange': '#dd6b20',
    'safe_green': '#276749',
    'grey': '#718096',
    'grey_light': '#a0aec0',
    'background': '#f7fafc',
    'white': '#ffffff'
}

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 12
plt.rcParams['axes.titlesize'] = 16
plt.rcParams['axes.titleweight'] = 'bold'
plt.rcParams['figure.facecolor'] = COLORS['background']
plt.rcParams['axes.facecolor'] = COLORS['white']
plt.rcParams['axes.edgecolor'] = COLORS['grey_light']
plt.rcParams['grid.color'] = COLORS['grey_light']
plt.rcParams['grid.alpha'] = 0.5

print("=" * 70)
print("INFOGRAPHICS GENERATOR - Pulse of Bharat")
print("=" * 70)

# ============================================================
# LOAD DATA
# ============================================================

print("\n[1] Loading data...")
governance_df = load_chunked_csv("governance_intelligence_master", low_memory=False)
governance_df['date'] = pd.to_datetime(governance_df['date'])

pincode_summary = pd.read_csv(BASE_DIR / "governance_pincode_summary.csv", low_memory=False)
dashboard_df = load_chunked_csv("final_aadhaar_risk_dashboard_data", low_memory=False)
dashboard_df['date'] = pd.to_datetime(dashboard_df['date'])

print(f"    Loaded governance data: {len(governance_df):,} records")
print(f"    Loaded pincode summary: {len(pincode_summary):,} records")
print(f"    Loaded dashboard data: {len(dashboard_df):,} records")

# ============================================================
# VISUAL 1: The Ghost Village Effect
# ============================================================

print("\n[2] Creating 'The Ghost Village Effect' infographic...")

fig, ax1 = plt.subplots(figsize=(14, 8))

# Get top 10 districts with highest school dropout risk
district_edu = governance_df.groupby('district').agg({
    'children_enrolled': 'sum',
    'bio_age_5_17': 'sum',
    'School_Dropout_Risk_Index': 'mean',
    'state': 'first'
}).reset_index()

# Calculate the "ghost children" - enrolled but no biometric verification
district_edu['missing_children'] = district_edu['children_enrolled'] - district_edu['bio_age_5_17']
district_edu['missing_children'] = district_edu['missing_children'].clip(lower=0)

top_ghost = district_edu.nlargest(10, 'School_Dropout_Risk_Index')

x = np.arange(len(top_ghost))
width = 0.35

# Bar chart for enrolled children
bars1 = ax1.bar(x - width/2, top_ghost['children_enrolled'], width, 
                label='Children Enrolled (Birth-17)', color=COLORS['navy'], alpha=0.8)

# Bar chart for verified (biometric)
bars2 = ax1.bar(x + width/2, top_ghost['bio_age_5_17'], width,
                label='Biometrically Verified', color=COLORS['safe_green'], alpha=0.8)

ax1.set_xlabel('District', fontsize=12, fontweight='bold')
ax1.set_ylabel('Number of Children', fontsize=12, fontweight='bold', color=COLORS['navy'])
ax1.set_xticks(x)
ax1.set_xticklabels([f"{d[:15]}..." if len(d) > 15 else d for d in top_ghost['district']], 
                     rotation=45, ha='right')
ax1.tick_params(axis='y', labelcolor=COLORS['navy'])

# Secondary axis for dropout risk
ax2 = ax1.twinx()
line = ax2.plot(x, top_ghost['School_Dropout_Risk_Index'], 'o-', 
                color=COLORS['alert_red'], linewidth=3, markersize=10, label='Dropout Risk Index')
ax2.set_ylabel('Dropout Risk Index (%)', fontsize=12, fontweight='bold', color=COLORS['alert_red'])
ax2.tick_params(axis='y', labelcolor=COLORS['alert_red'])
ax2.set_ylim(0, 100)

# Add gap annotations
for i, (enrolled, verified) in enumerate(zip(top_ghost['children_enrolled'], top_ghost['bio_age_5_17'])):
    gap = enrolled - verified
    if gap > 0:
        ax1.annotate(f'Gap: {int(gap):,}', xy=(i, enrolled), 
                    xytext=(i, enrolled + enrolled*0.05),
                    ha='center', fontsize=9, color=COLORS['alert_red'], fontweight='bold')

# Title and legend
plt.title('THE GHOST VILLAGE EFFECT\nWhere Are the Missing Children?', 
          fontsize=18, fontweight='bold', color=COLORS['navy'], pad=20)

# Combined legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', framealpha=0.9)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '01_ghost_village_effect.png', dpi=300, bbox_inches='tight', 
            facecolor=COLORS['background'])
plt.close()
print("    Saved: 01_ghost_village_effect.png")

# ============================================================
# VISUAL 2: The Infiltration Spike
# ============================================================

print("\n[3] Creating 'The Infiltration Spike' infographic...")

fig, ax = plt.subplots(figsize=(14, 8))

# Get daily aggregated adult enrollments
daily_adults = dashboard_df.groupby('date').agg({
    'total_enrolment': 'sum',
    'total_demographic': 'sum',
    'rolling_7d_demographic': 'sum',
    'Sudden_Spike_Anomaly': 'sum'
}).reset_index()

# Calculate rolling average
daily_adults['rolling_avg'] = daily_adults['total_demographic'].rolling(window=7, min_periods=1).mean()

# Find spike dates (where spikes > threshold)
spike_threshold = daily_adults['rolling_avg'].mean() * 3
spike_dates = daily_adults[daily_adults['total_demographic'] > spike_threshold]

# Plot main line
ax.fill_between(daily_adults['date'], daily_adults['total_demographic'], 
                alpha=0.3, color=COLORS['navy'])
ax.plot(daily_adults['date'], daily_adults['total_demographic'], 
        color=COLORS['navy'], linewidth=2, label='Daily Demographic Updates')

# Plot rolling average
ax.plot(daily_adults['date'], daily_adults['rolling_avg'], 
        color=COLORS['grey'], linewidth=2, linestyle='--', label='7-Day Rolling Average')

# Plot 300% threshold line
ax.axhline(y=spike_threshold, color=COLORS['warning_orange'], linestyle=':', 
           linewidth=2, label='300% Threshold (Security Alert)')

# Highlight spike points
if len(spike_dates) > 0:
    ax.scatter(spike_dates['date'], spike_dates['total_demographic'], 
               s=200, c=COLORS['alert_red'], zorder=5, edgecolors='white', linewidths=2)
    
    # Annotate the biggest spike
    max_spike = spike_dates.nlargest(1, 'total_demographic').iloc[0]
    ax.annotate('⚠️ POTENTIAL SECURITY THREAT\nUnusual Demographic Spike',
                xy=(max_spike['date'], max_spike['total_demographic']),
                xytext=(max_spike['date'], max_spike['total_demographic'] * 1.15),
                ha='center', fontsize=11, fontweight='bold', color=COLORS['alert_red'],
                arrowprops=dict(arrowstyle='->', color=COLORS['alert_red'], lw=2),
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor=COLORS['alert_red']))

# Formatting
ax.set_xlabel('Date', fontsize=12, fontweight='bold')
ax.set_ylabel('Demographic Updates (Address Changes)', fontsize=12, fontweight='bold')
ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: format(int(x), ',')))

plt.title('THE INFILTRATION SPIKE\nAnomalous Demographic Activity Detection', 
          fontsize=18, fontweight='bold', color=COLORS['navy'], pad=20)
ax.legend(loc='upper left', framealpha=0.9)

# Add summary box
total_spikes = len(spike_dates)
summary_text = f"Total Spike Events: {total_spikes}\nPeak Value: {daily_adults['total_demographic'].max():,.0f}"
ax.text(0.98, 0.95, summary_text, transform=ax.transAxes, 
        fontsize=11, verticalalignment='top', horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor=COLORS['navy'], alpha=0.8),
        color='white', fontweight='bold')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '02_infiltration_spike.png', dpi=300, bbox_inches='tight',
            facecolor=COLORS['background'])
plt.close()
print("    Saved: 02_infiltration_spike.png")

# ============================================================
# VISUAL 3: Neighbor Variance Map (Scatter)
# ============================================================

print("\n[4] Creating 'Neighbor Variance Map' infographic...")

fig, ax = plt.subplots(figsize=(12, 10))

# Get pincode data with risk scores
# We'll use governance scores vs max risk (which represents neighbor comparison anomalies)
scatter_data = pincode_summary.sample(min(2000, len(pincode_summary)), random_state=42)

# Create risk categories
def categorize_anomaly(row):
    gov_score = row['Governance_Risk_Score']
    # Use max_risk_score if available, otherwise derive from governance
    neighbor_proxy = row.get('max_risk_score', gov_score * 0.8)
    
    if gov_score > 50 and neighbor_proxy < 30:
        return 'Local Anomaly (High Risk, Low Neighbors)'
    elif gov_score < 30 and neighbor_proxy > 50:
        return 'Regional Issue (Low Risk, High Neighbors)'
    elif gov_score > 50 and neighbor_proxy > 50:
        return 'Regional Crisis'
    else:
        return 'Normal'

scatter_data['anomaly_type'] = scatter_data.apply(categorize_anomaly, axis=1)

# Color mapping
color_map = {
    'Local Anomaly (High Risk, Low Neighbors)': COLORS['alert_red'],
    'Regional Issue (Low Risk, High Neighbors)': COLORS['warning_orange'],
    'Regional Crisis': COLORS['navy'],
    'Normal': COLORS['grey_light']
}

# Plot each category
for anomaly_type, color in color_map.items():
    subset = scatter_data[scatter_data['anomaly_type'] == anomaly_type]
    ax.scatter(subset['Governance_Risk_Score'], 
               subset.get('max_risk_score', subset['Governance_Risk_Score'] * 0.8),
               c=color, label=f'{anomaly_type} ({len(subset)})', alpha=0.6, s=50,
               edgecolors='white', linewidths=0.5)

# Add diagonal reference line
ax.plot([0, 100], [0, 100], 'k--', alpha=0.3, label='Equal Risk Line')

# Highlight quadrants
ax.axhline(y=50, color=COLORS['grey'], linestyle=':', alpha=0.5)
ax.axvline(x=50, color=COLORS['grey'], linestyle=':', alpha=0.5)

# Labels for quadrants
ax.text(75, 25, 'LOCAL\nANOMALY\nZONE', ha='center', va='center', fontsize=12, 
        fontweight='bold', color=COLORS['alert_red'], alpha=0.7)
ax.text(25, 75, 'REGIONAL\nISSUE\nZONE', ha='center', va='center', fontsize=12,
        fontweight='bold', color=COLORS['warning_orange'], alpha=0.7)

ax.set_xlabel('Pincode Governance Risk Score', fontsize=12, fontweight='bold')
ax.set_ylabel('Neighbor/Regional Risk Score', fontsize=12, fontweight='bold')
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)

plt.title('NEIGHBOR VARIANCE MAP\nIdentifying Local vs Regional Anomalies', 
          fontsize=18, fontweight='bold', color=COLORS['navy'], pad=20)
ax.legend(loc='lower right', framealpha=0.9)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '03_neighbor_variance_map.png', dpi=300, bbox_inches='tight',
            facecolor=COLORS['background'])
plt.close()
print("    Saved: 03_neighbor_variance_map.png")

# ============================================================
# VISUAL 4: Multi-Sector Risk Dashboard
# ============================================================

print("\n[5] Creating 'Multi-Sector Risk Dashboard' infographic...")

fig, axes = plt.subplots(2, 3, figsize=(18, 12))
fig.suptitle('PULSE OF BHARAT - MULTI-SECTOR RISK DASHBOARD', 
             fontsize=20, fontweight='bold', color=COLORS['navy'], y=1.02)

# Sector data
sectors = [
    ('Education', 'School_Dropout_Risk_Index', '📚', COLORS['navy']),
    ('Hunger/Ration', 'Migrant_Hunger_Score', '🍚', COLORS['warning_orange']),
    ('Rural Development', 'Village_Hollow_Out_Rate', '🏘️', COLORS['safe_green']),
    ('Electoral', 'Electoral_Discrepancy_Index', '🗳️', COLORS['alert_red']),
    ('Labor Migration', 'Skill_Gap_Migration_Flow', '👷', COLORS['navy_light']),
]

# State-level aggregation for each sector
state_data = pincode_summary.groupby('state').agg({
    'School_Dropout_Risk_Index': 'mean',
    'Migrant_Hunger_Score': 'mean',
    'Village_Hollow_Out_Rate': 'mean',
    'Electoral_Discrepancy_Index': 'mean',
    'Skill_Gap_Migration_Flow': 'mean',
    'Governance_Risk_Score': 'mean',
    'pincode': 'count'
}).reset_index()
state_data.columns = list(state_data.columns[:-1]) + ['pincode_count']

for idx, (name, metric, icon, color) in enumerate(sectors):
    ax = axes[idx // 3, idx % 3]
    
    top_states = state_data.nlargest(8, metric)
    
    bars = ax.barh(top_states['state'], top_states[metric], color=color, alpha=0.8)
    
    # Add value labels
    for bar, val in zip(bars, top_states[metric]):
        ax.text(val + 1, bar.get_y() + bar.get_height()/2, f'{val:.1f}', 
                va='center', fontsize=10, fontweight='bold', color=COLORS['navy'])
    
    ax.set_xlabel('Risk Index', fontsize=11, fontweight='bold')
    ax.set_title(f'{icon} {name}', fontsize=14, fontweight='bold', color=color)
    ax.set_xlim(0, max(top_states[metric]) * 1.2)
    ax.invert_yaxis()

# Overall summary in 6th slot
ax = axes[1, 2]
risk_levels = ['Critical', 'High', 'Medium', 'Low', 'Safe']
risk_counts = [
    (pincode_summary['Governance_Risk_Score'] >= 70).sum(),
    ((pincode_summary['Governance_Risk_Score'] >= 50) & (pincode_summary['Governance_Risk_Score'] < 70)).sum(),
    ((pincode_summary['Governance_Risk_Score'] >= 30) & (pincode_summary['Governance_Risk_Score'] < 50)).sum(),
    ((pincode_summary['Governance_Risk_Score'] >= 10) & (pincode_summary['Governance_Risk_Score'] < 30)).sum(),
    (pincode_summary['Governance_Risk_Score'] < 10).sum()
]
risk_colors = [COLORS['alert_red'], COLORS['warning_orange'], '#f6e05e', COLORS['safe_green'], COLORS['navy']]

wedges, texts, autotexts = ax.pie(risk_counts, labels=risk_levels, colors=risk_colors,
                                   autopct='%1.1f%%', startangle=90,
                                   explode=[0.1 if i == 0 else 0 for i in range(5)])
ax.set_title('🎯 Overall Risk Distribution', fontsize=14, fontweight='bold', color=COLORS['navy'])

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '04_multi_sector_dashboard.png', dpi=300, bbox_inches='tight',
            facecolor=COLORS['background'])
plt.close()
print("    Saved: 04_multi_sector_dashboard.png")

# ============================================================
# VISUAL 5: Time Series Trend Analysis
# ============================================================

print("\n[6] Creating 'Time Series Trend Analysis' infographic...")

fig, axes = plt.subplots(3, 1, figsize=(16, 14), sharex=True)
fig.suptitle('TEMPORAL ANALYSIS: ENROLLMENT, DEMOGRAPHIC & BIOMETRIC TRENDS', 
             fontsize=18, fontweight='bold', color=COLORS['navy'], y=0.98)

# Daily aggregates
daily_trends = dashboard_df.groupby('date').agg({
    'total_enrolment': 'sum',
    'total_demographic': 'sum',
    'total_biometric': 'sum',
    'Sudden_Spike_Anomaly': 'sum',
    'Risk_Score': 'mean'
}).reset_index()

# Enrollment trend
ax1 = axes[0]
ax1.fill_between(daily_trends['date'], daily_trends['total_enrolment'], 
                 alpha=0.3, color=COLORS['navy'])
ax1.plot(daily_trends['date'], daily_trends['total_enrolment'], 
         color=COLORS['navy'], linewidth=2)
ax1.set_ylabel('New Enrollments', fontsize=11, fontweight='bold', color=COLORS['navy'])
ax1.set_title('📊 Daily Aadhaar Enrollments', fontsize=13, fontweight='bold', loc='left')
ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x/1000:.0f}K'))

# Demographic trend
ax2 = axes[1]
ax2.fill_between(daily_trends['date'], daily_trends['total_demographic'], 
                 alpha=0.3, color=COLORS['warning_orange'])
ax2.plot(daily_trends['date'], daily_trends['total_demographic'], 
         color=COLORS['warning_orange'], linewidth=2)
ax2.set_ylabel('Demographic Updates', fontsize=11, fontweight='bold', color=COLORS['warning_orange'])
ax2.set_title('📍 Daily Demographic Updates (Address Changes)', fontsize=13, fontweight='bold', loc='left')
ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x/1000:.0f}K'))

# Anomaly count trend
ax3 = axes[2]
ax3.bar(daily_trends['date'], daily_trends['Sudden_Spike_Anomaly'], 
        color=COLORS['alert_red'], alpha=0.7, width=1)
ax3.set_ylabel('Spike Anomalies', fontsize=11, fontweight='bold', color=COLORS['alert_red'])
ax3.set_xlabel('Date', fontsize=12, fontweight='bold')
ax3.set_title('🚨 Daily Anomaly Detections', fontsize=13, fontweight='bold', loc='left')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '05_time_series_trends.png', dpi=300, bbox_inches='tight',
            facecolor=COLORS['background'])
plt.close()
print("    Saved: 05_time_series_trends.png")

# ============================================================
# VISUAL 6: Geographic Heatmap by State
# ============================================================

print("\n[7] Creating 'State-wise Risk Heatmap' infographic...")

fig, ax = plt.subplots(figsize=(14, 10))

# Prepare heatmap data
heatmap_data = state_data.set_index('state')[
    ['School_Dropout_Risk_Index', 'Migrant_Hunger_Score', 'Village_Hollow_Out_Rate',
     'Electoral_Discrepancy_Index', 'Skill_Gap_Migration_Flow']
].head(20)

heatmap_data.columns = ['Education', 'Hunger', 'Rural Dev', 'Electoral', 'Labor']

# Create heatmap
sns.heatmap(heatmap_data, annot=True, fmt='.1f', cmap='RdYlGn_r',
            linewidths=0.5, linecolor='white', ax=ax,
            cbar_kws={'label': 'Risk Index'})

ax.set_title('STATE-WISE SECTOR RISK HEATMAP\nDarker = Higher Risk', 
             fontsize=16, fontweight='bold', color=COLORS['navy'], pad=20)
ax.set_xlabel('Sector', fontsize=12, fontweight='bold')
ax.set_ylabel('State', fontsize=12, fontweight='bold')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '06_state_risk_heatmap.png', dpi=300, bbox_inches='tight',
            facecolor=COLORS['background'])
plt.close()
print("    Saved: 06_state_risk_heatmap.png")

# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("INFOGRAPHICS GENERATION COMPLETE")
print("=" * 70)

print(f"\n📁 Output Directory: {OUTPUT_DIR}")
print("\n📊 Generated Visuals:")
print("    1. 01_ghost_village_effect.png - Education sector analysis")
print("    2. 02_infiltration_spike.png - Temporal anomaly detection")
print("    3. 03_neighbor_variance_map.png - Local vs regional anomalies")
print("    4. 04_multi_sector_dashboard.png - 5-sector overview")
print("    5. 05_time_series_trends.png - Daily trend analysis")
print("    6. 06_state_risk_heatmap.png - State-wise risk comparison")

print("\n✅ All infographics ready for presentation!")
print("=" * 70)
