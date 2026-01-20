"""
CSV Utilities for Chunked File Loading
======================================
Provides helper functions to load CSVs that have been split into chunks.
This is required because GitHub has a 100MB file size limit.

Large CSVs are stored in the chunked_data/ folder with pattern:
    <filename>_chunk_0.csv, <filename>_chunk_1.csv, etc.

Usage:
    from csv_utils import load_chunked_csv
    df = load_chunked_csv("processed_aadhaar_risk_data")
"""

import pandas as pd
from pathlib import Path
import glob

# Base directory for the project
BASE_DIR = Path(__file__).parent

# Directory where chunked CSVs are stored
CHUNKED_DIR = BASE_DIR / "chunked_data"

# Mapping of original filenames to their chunked versions
CHUNKED_FILES = {
    "processed_aadhaar_risk_data.csv": "processed_aadhaar_risk_data",
    "governance_intelligence_master.csv": "governance_intelligence_master", 
    "final_aadhaar_risk_dashboard_data.csv": "final_aadhaar_risk_dashboard_data"
}


def load_chunked_csv(base_name: str, low_memory: bool = False) -> pd.DataFrame:
    """
    Load a CSV that has been split into chunks.
    
    Args:
        base_name: The base filename (with or without .csv extension)
                  e.g., "processed_aadhaar_risk_data" or "processed_aadhaar_risk_data.csv"
        low_memory: Whether to use low_memory mode for pandas (default False)
    
    Returns:
        pd.DataFrame: Concatenated DataFrame from all chunks
    
    Example:
        df = load_chunked_csv("governance_intelligence_master")
    """
    # Remove .csv extension if present
    if base_name.endswith('.csv'):
        base_name = base_name[:-4]
    
    # Find all chunk files (support both naming patterns: _chunk_* and _part*)
    chunk_files = []
    for pattern_suffix in ["_chunk_*.csv", "_part*.csv"]:
        pattern = CHUNKED_DIR / f"{base_name}{pattern_suffix}"
        chunk_files = sorted(glob.glob(str(pattern)))
        if chunk_files:
            break
    
    if not chunk_files:
        # Fallback: try loading the original file directly (for local dev with large files)
        original_file = BASE_DIR / f"{base_name}.csv"
        if original_file.exists():
            print(f"Loading original file: {original_file.name}")
            return pd.read_csv(original_file, low_memory=low_memory)
        else:
            raise FileNotFoundError(
                f"No chunks found for '{base_name}' in {CHUNKED_DIR} "
                f"and original file not found at {original_file}"
            )
    
    print(f"Loading {len(chunk_files)} chunks for '{base_name}'...")
    
    # Load and concatenate all chunks
    dfs = []
    for chunk_file in chunk_files:
        df_chunk = pd.read_csv(chunk_file, low_memory=low_memory)
        dfs.append(df_chunk)
        print(f"  Loaded {Path(chunk_file).name}: {len(df_chunk):,} rows")
    
    combined_df = pd.concat(dfs, ignore_index=True)
    print(f"  Total: {len(combined_df):,} rows")
    
    return combined_df


def save_chunked_csv(df: pd.DataFrame, base_name: str, chunk_size_mb: int = 90) -> list:
    """
    Save a DataFrame as multiple chunks to stay under GitHub's file size limit.
    
    Args:
        df: DataFrame to save
        base_name: Base filename (without .csv extension)
        chunk_size_mb: Target chunk size in MB (default 90 to stay under 100MB limit)
    
    Returns:
        list: Paths to all chunk files created
    """
    # Remove .csv extension if present
    if base_name.endswith('.csv'):
        base_name = base_name[:-4]
    
    # Ensure chunked directory exists
    CHUNKED_DIR.mkdir(exist_ok=True)
    
    # Estimate rows per chunk based on target size
    # First, estimate bytes per row from a sample
    sample_size = min(1000, len(df))
    sample_csv = df.head(sample_size).to_csv(index=False)
    bytes_per_row = len(sample_csv.encode('utf-8')) / sample_size
    
    target_bytes = chunk_size_mb * 1024 * 1024
    rows_per_chunk = max(1, int(target_bytes / bytes_per_row))
    
    chunk_files = []
    total_rows = len(df)
    chunk_idx = 0
    
    for start in range(0, total_rows, rows_per_chunk):
        end = min(start + rows_per_chunk, total_rows)
        chunk_df = df.iloc[start:end]
        
        chunk_path = CHUNKED_DIR / f"{base_name}_chunk_{chunk_idx}.csv"
        chunk_df.to_csv(chunk_path, index=False)
        chunk_files.append(str(chunk_path))
        
        print(f"  Saved {chunk_path.name}: {len(chunk_df):,} rows")
        chunk_idx += 1
    
    print(f"  Created {len(chunk_files)} chunks for '{base_name}'")
    return chunk_files


def get_available_datasets() -> dict:
    """
    List all available chunked datasets.
    
    Returns:
        dict: Mapping of dataset names to their chunk count
    """
    datasets = {}
    
    if not CHUNKED_DIR.exists():
        return datasets
    
    for csv_file in CHUNKED_DIR.glob("*_chunk_0.csv"):
        base_name = csv_file.name.replace("_chunk_0.csv", "")
        pattern = CHUNKED_DIR / f"{base_name}_chunk_*.csv"
        chunk_count = len(glob.glob(str(pattern)))
        datasets[base_name] = chunk_count
    
    return datasets


if __name__ == "__main__":
    # Test the utility
    print("Available chunked datasets:")
    for name, count in get_available_datasets().items():
        print(f"  {name}: {count} chunks")
