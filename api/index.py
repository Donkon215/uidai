"""
Vercel Serverless Function Entry Point
======================================
ASGI adapter for Vercel deployment

Note: ML models disabled for serverless constraints.
For full ML capabilities, deploy using Docker or Cloud VM.
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Override environment for serverless
os.environ.setdefault('ML_ENABLED', 'False')

from backend.main import app

# Vercel handler
handler = app
