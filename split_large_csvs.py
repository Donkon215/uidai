"""
Split large CSV files into smaller chunks (< 100 MB) for GitHub compatibility.
"""
import os
import pandas as pd
import math

# Files to split (those exceeding 100 MB)
LARGE_FILES = [
    "processed_aadhaar_risk_data.csv",
    "governance_intelligence_master.csv",
    "final_aadhaar_risk_dashboard_data.csv",
]

MAX_SIZE_MB = 90  # Target size per chunk (leaving margin under 100 MB)

def get_file_size_mb(filepath):
    """Get file size in MB."""
    return os.path.getsize(filepath) / (1024 * 1024)

def split_csv(filepath, max_size_mb=MAX_SIZE_MB):
    """Split a CSV file into chunks smaller than max_size_mb."""
    if not os.path.exists(filepath):
        print(f"  [SKIP] File not found: {filepath}")
        return []
    
    file_size_mb = get_file_size_mb(filepath)
    print(f"  Original size: {file_size_mb:.2f} MB")
    
    if file_size_mb <= max_size_mb:
        print(f"  [SKIP] File already under {max_size_mb} MB")
        return []
    
    # Read the CSV
    print(f"  Reading CSV...")
    df = pd.read_csv(filepath, low_memory=False)
    total_rows = len(df)
    print(f"  Total rows: {total_rows:,}")
    
    # Estimate number of chunks needed
    num_chunks = math.ceil(file_size_mb / max_size_mb)
    rows_per_chunk = math.ceil(total_rows / num_chunks)
    print(f"  Splitting into ~{num_chunks} chunks ({rows_per_chunk:,} rows each)")
    
    # Create output directory
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    output_dir = os.path.join(os.path.dirname(filepath), f"{base_name}_chunks")
    os.makedirs(output_dir, exist_ok=True)
    
    # Split and save chunks
    chunk_files = []
    for i in range(num_chunks):
        start_idx = i * rows_per_chunk
        end_idx = min((i + 1) * rows_per_chunk, total_rows)
        chunk_df = df.iloc[start_idx:end_idx]
        
        chunk_filename = f"{base_name}_part{i+1:02d}.csv"
        chunk_path = os.path.join(output_dir, chunk_filename)
        chunk_df.to_csv(chunk_path, index=False)
        
        chunk_size = get_file_size_mb(chunk_path)
        print(f"    Created: {chunk_filename} ({chunk_size:.2f} MB, {len(chunk_df):,} rows)")
        chunk_files.append(chunk_path)
    
    return chunk_files

def main():
    print("=" * 60)
    print("Splitting large CSV files for GitHub compatibility")
    print("=" * 60)
    
    all_chunks = []
    for filename in LARGE_FILES:
        filepath = os.path.join(os.path.dirname(__file__) or ".", filename)
        print(f"\nProcessing: {filename}")
        chunks = split_csv(filepath)
        all_chunks.extend(chunks)
    
    print("\n" + "=" * 60)
    print(f"Done! Created {len(all_chunks)} chunk files.")
    print("=" * 60)
    
    # Print .gitignore entries
    print("\nAdd these to .gitignore to exclude original large files:")
    for filename in LARGE_FILES:
        print(f"  {filename}")

if __name__ == "__main__":
    main()
