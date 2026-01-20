"""
Simple server runner for Pulse of Bharat API
"""
import uvicorn

if __name__ == "__main__":
    print("Starting Pulse of Bharat API Server...")
    print("Server will be available at: http://127.0.0.1:8000")
    print("API Documentation: http://127.0.0.1:8000/docs")
    print("\nPress CTRL+C to stop the server\n")
    
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )
