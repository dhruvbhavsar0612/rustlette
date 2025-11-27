#!/usr/bin/env python3
"""
FastAPI benchmark application.

This creates a standard set of endpoints for benchmarking FastAPI
against other Python web frameworks.
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import time
from typing import Dict, Any, Optional, List

# Create the FastAPI application
app = FastAPI()

# Sample data for testing
SAMPLE_USERS = {
    1: {"id": 1, "name": "Alice", "email": "alice@example.com", "active": True},
    2: {"id": 2, "name": "Bob", "email": "bob@example.com", "active": False},
    3: {"id": 3, "name": "Charlie", "email": "charlie@example.com", "active": True},
}

# Statistics tracking
stats = {
    "requests": 0,
    "start_time": time.time(),
}


# Pydantic models
class User(BaseModel):
    name: str
    email: str
    active: bool = True


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    active: bool
    created_at: Optional[float] = None


class EchoRequest(BaseModel):
    data: Any


@app.get("/")
async def root():
    """Simple JSON response endpoint."""
    stats["requests"] += 1
    return {
        "message": "Hello from FastAPI!",
        "framework": "fastapi",
        "timestamp": time.time(),
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "framework": "fastapi"}


@app.get("/json")
async def json_response():
    """JSON response with more complex data."""
    stats["requests"] += 1
    return {
        "users": list(SAMPLE_USERS.values()),
        "total": len(SAMPLE_USERS),
        "generated_at": time.time(),
        "server": "fastapi",
    }


@app.get("/text")
async def text_response():
    """Plain text response."""
    stats["requests"] += 1
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse("Hello from FastAPI! This is a plain text response.")


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get user by ID with path parameter."""
    stats["requests"] += 1

    if user_id not in SAMPLE_USERS:
        raise HTTPException(
            status_code=404, detail={"error": "User not found", "user_id": user_id}
        )

    return SAMPLE_USERS[user_id]


@app.get("/search")
async def search_users(q: str = Query(""), limit: int = Query(10)):
    """Search endpoint with query parameters."""
    stats["requests"] += 1

    # Simple search simulation
    results = []
    for user in SAMPLE_USERS.values():
        if q.lower() in user["name"].lower() or q.lower() in user["email"].lower():
            results.append(user)
        if len(results) >= limit:
            break

    return {
        "query": q,
        "results": results,
        "total": len(results),
        "limit": limit,
    }


@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(user: User):
    """Create user endpoint (POST with JSON body)."""
    stats["requests"] += 1

    # Simulate user creation
    new_id = max(SAMPLE_USERS.keys()) + 1 if SAMPLE_USERS else 1
    new_user = {
        "id": new_id,
        "name": user.name,
        "email": user.email,
        "active": user.active,
        "created_at": time.time(),
    }

    SAMPLE_USERS[new_id] = new_user

    return new_user


@app.post("/echo")
async def echo(request_data: dict):
    """Echo endpoint that returns the request body."""
    stats["requests"] += 1

    return {
        "method": "POST",
        "echo": request_data,
        "timestamp": time.time(),
    }


@app.get("/stats")
async def get_stats():
    """Get server statistics."""
    uptime = time.time() - stats["start_time"]
    return {
        "framework": "fastapi",
        "requests_served": stats["requests"],
        "uptime_seconds": uptime,
        "requests_per_second": stats["requests"] / uptime if uptime > 0 else 0,
    }


@app.get("/heavy")
async def heavy_computation():
    """Endpoint that does some computation to test CPU performance."""
    stats["requests"] += 1

    # Simple computation
    result = 0
    for i in range(10000):
        result += i * i

    return {
        "computation_result": result,
        "iterations": 10000,
        "framework": "fastapi",
    }


# Event handlers
@app.on_event("startup")
async def startup():
    print("FastAPI benchmark app starting...")
    stats["start_time"] = time.time()


@app.on_event("shutdown")
async def shutdown():
    print("FastAPI benchmark app shutting down...")
    print(f"Total requests served: {stats['requests']}")


# Import moved to function level to avoid import order issues

if __name__ == "__main__":
    import uvicorn

    print("Starting FastAPI benchmark server...")
    uvicorn.run(app, host="127.0.0.1", port=8001, access_log=False, log_level="warning")
