# Vercel Configuration for Pulse of Bharat
# This configuration optimizes the app for Vercel's serverless limits

# Load only 1 chunk instead of 4 (430K records instead of 1.7M)
# This keeps memory usage under 1GB and startup time under 10s

# In backend/main.py, update the data loading section:
# Change this line:
# governance_master = load_chunked_csv(chunked_dir, 'governance_intelligence_master', num_chunks=4)
# To:
# governance_master = load_chunked_csv(chunked_dir, 'governance_intelligence_master', num_chunks=1)

# This will load only governance_intelligence_master_part01.csv (430,483 records)
# which is sufficient for demo purposes and works within Vercel limits
