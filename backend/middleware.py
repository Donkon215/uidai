"""
Production-Grade Error Handling & Monitoring Utilities
======================================================
Comprehensive error handlers, validators, and monitoring tools
"""

from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, validator
from typing import Optional, Any, Dict
import logging
import time
import psutil
import traceback
from datetime import datetime
from collections import defaultdict
import asyncio

logger = logging.getLogger(__name__)

# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class PincodeNotFoundException(HTTPException):
    def __init__(self, pincode: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pincode {pincode} not found in database"
        )

class DistrictNotFoundException(HTTPException):
    def __init__(self, district: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"District '{district}' not found in database"
        )

class DataNotLoadedException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data not loaded. Please wait for initialization."
        )

class InvalidPincodeException(HTTPException):
    def __init__(self, pincode: int):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid pincode format: {pincode}. Must be 6-digit number (100000-999999)"
        )

class RateLimitExceededException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )

# =============================================================================
# VALIDATION MODELS
# =============================================================================

class PincodeRequest(BaseModel):
    pincode: int
    
    @validator('pincode')
    def validate_pincode(cls, v):
        if not (100000 <= v <= 999999):
            raise ValueError("Pincode must be a 6-digit number")
        return v

class SectorQuery(BaseModel):
    sector: str = "all"
    
    @validator('sector')
    def validate_sector(cls, v):
        valid_sectors = ["all", "education", "hunger", "rural", "electoral", "labor"]
        if v.lower() not in valid_sectors:
            raise ValueError(f"Invalid sector. Must be one of: {', '.join(valid_sectors)}")
        return v.lower()

class ForecastRequest(BaseModel):
    pincode: Optional[int] = None
    district: Optional[str] = None
    horizon: int = 5
    
    @validator('horizon')
    def validate_horizon(cls, v):
        if v not in [1, 5, 10]:
            raise ValueError("Forecast horizon must be 1, 5, or 10 years")
        return v

# =============================================================================
# ERROR HANDLERS
# =============================================================================

async def custom_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler"""
    error_id = f"ERR-{int(time.time())}"
    
    logger.error(
        f"Error ID: {error_id} | Path: {request.url.path} | "
        f"Method: {request.method} | Error: {str(exc)}\n"
        f"Traceback: {traceback.format_exc()}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "error_id": error_id,
                "message": "Internal server error occurred",
                "type": type(exc).__name__,
                "timestamp": datetime.now().isoformat()
            },
            "suggestion": "Please contact support with the error ID"
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(f"Validation error on {request.url.path}: {errors}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "message": "Validation error",
                "details": errors,
                "timestamp": datetime.now().isoformat()
            }
        }
    )

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP {exc.status_code} on {request.url.path}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "path": request.url.path,
                "timestamp": datetime.now().isoformat()
            }
        }
    )

# =============================================================================
# RATE LIMITING
# =============================================================================

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_requests: int = 100, window: int = 60):
        self.max_requests = max_requests
        self.window = window  # seconds
        self.requests = defaultdict(list)
        self._cleanup_task = None
    
    def start_cleanup(self):
        """Start background cleanup task"""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def _periodic_cleanup(self):
        """Periodically clean old requests"""
        while True:
            await asyncio.sleep(self.window)
            current_time = time.time()
            cutoff = current_time - self.window
            
            # Clean old entries
            for ip in list(self.requests.keys()):
                self.requests[ip] = [t for t in self.requests[ip] if t > cutoff]
                if not self.requests[ip]:
                    del self.requests[ip]
    
    async def check_rate_limit(self, client_ip: str) -> bool:
        """Check if request is within rate limit"""
        current_time = time.time()
        cutoff = current_time - self.window
        
        # Remove old requests
        self.requests[client_ip] = [t for t in self.requests[client_ip] if t > cutoff]
        
        # Check limit
        if len(self.requests[client_ip]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return False
        
        # Add current request
        self.requests[client_ip].append(current_time)
        return True

# =============================================================================
# REQUEST LOGGING MIDDLEWARE
# =============================================================================

class RequestLoggingMiddleware:
    """Log all requests with timing"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        start_time = time.time()
        request = Request(scope, receive)
        
        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request
        try:
            await self.app(scope, receive, send)
        finally:
            # Log completion
            duration = time.time() - start_time
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"in {duration:.3f}s"
            )

# =============================================================================
# HEALTH MONITORING
# =============================================================================

class HealthMonitor:
    """System health monitoring"""
    
    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.slow_requests = 0
    
    def increment_request(self):
        self.request_count += 1
    
    def increment_error(self):
        self.error_count += 1
    
    def increment_slow_request(self):
        self.slow_requests += 1
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system health metrics"""
        uptime = time.time() - self.start_time
        
        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "status": "healthy" if cpu_percent < 90 and memory.percent < 90 else "degraded",
            "uptime_seconds": int(uptime),
            "uptime_human": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m",
            "system": {
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(memory.percent, 2),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": round(disk.percent, 2),
                "disk_free_gb": round(disk.free / (1024**3), 2)
            },
            "application": {
                "total_requests": self.request_count,
                "total_errors": self.error_count,
                "slow_requests": self.slow_requests,
                "error_rate": round(self.error_count / max(self.request_count, 1) * 100, 2)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def is_healthy(self) -> bool:
        """Check if system is healthy"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Health checks
            checks = [
                cpu_percent < 95,
                memory.percent < 95,
                disk.percent < 95,
                self.error_count / max(self.request_count, 1) < 0.1  # < 10% error rate
            ]
            
            return all(checks)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

# =============================================================================
# DATA VALIDATORS
# =============================================================================

def validate_dataframe_loaded(df) -> bool:
    """Validate that DataFrame is loaded and not empty"""
    if df is None or df.empty:
        raise DataNotLoadedException()
    return True

def validate_pincode_exists(df, pincode: int) -> bool:
    """Validate that pincode exists in DataFrame"""
    if not (100000 <= pincode <= 999999):
        raise InvalidPincodeException(pincode)
    
    if pincode not in df['pincode'].values:
        raise PincodeNotFoundException(pincode)
    
    return True

def validate_district_exists(df, district: str) -> bool:
    """Validate that district exists in DataFrame"""
    if district not in df['district'].values:
        raise DistrictNotFoundException(district)
    
    return True

def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float"""
    try:
        result = float(value)
        return result if not (result != result) else default  # NaN check
    except (TypeError, ValueError):
        return default

def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

# =============================================================================
# PERFORMANCE MONITORING
# =============================================================================

class PerformanceMonitor:
    """Monitor API endpoint performance"""
    
    def __init__(self):
        self.endpoint_stats = defaultdict(lambda: {
            "count": 0,
            "total_time": 0.0,
            "min_time": float('inf'),
            "max_time": 0.0
        })
    
    def record(self, endpoint: str, duration: float):
        """Record endpoint execution time"""
        stats = self.endpoint_stats[endpoint]
        stats["count"] += 1
        stats["total_time"] += duration
        stats["min_time"] = min(stats["min_time"], duration)
        stats["max_time"] = max(stats["max_time"], duration)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        result = {}
        for endpoint, stats in self.endpoint_stats.items():
            result[endpoint] = {
                "calls": stats["count"],
                "avg_time_ms": round(stats["total_time"] / stats["count"] * 1000, 2),
                "min_time_ms": round(stats["min_time"] * 1000, 2),
                "max_time_ms": round(stats["max_time"] * 1000, 2)
            }
        return result

# Initialize global instances
health_monitor = HealthMonitor()
performance_monitor = PerformanceMonitor()
