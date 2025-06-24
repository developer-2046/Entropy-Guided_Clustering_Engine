from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import time
import redis.asyncio as redis
import os

class RateLimitMiddleware:
    """Rate limiting middleware."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        
    async def __call__(self, request: Request, call_next):
        # Extract API key or use IP
        api_key = request.headers.get("X-API-Key")
        identifier = api_key or request.client.host
        
        # Rate limit key
        rate_key = f"rate_limit:{identifier}"
        
        # Check current count
        current = await self.redis_client.get(rate_key)
        if current and int(current) > 100:  # 100 requests per minute
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Increment counter
        pipe = self.redis_client.pipeline()
        pipe.incr(rate_key)
        pipe.expire(rate_key, 60)  # 1 minute window
        await pipe.execute()
        
        response = await call_next(request)
        return response

class MetricsMiddleware:
    """Metrics collection middleware."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
    
    async def __call__(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Store metrics
        await self.redis_client.lpush(
            "api_response_times",
            f"{request.url.path}:{response.status_code}:{response_time:.3f}"
        )
        await self.redis_client.ltrim("api_response_times", 0, 1000)  # Keep last 1000
        
        return response