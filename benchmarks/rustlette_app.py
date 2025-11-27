#!/usr/bin/env python3
"""
Rustlette benchmark application.

This creates a standard set of endpoints for benchmarking Rustlette
against other Python web frameworks.
"""

import rustlette
import json
import time
from typing import Dict, Any

# Create the Rustlette application
app = rustlette.Rustlette(debug=False)

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


@app.route("/")
async def root(request):
    """Simple JSON response endpoint."""
    stats["requests"] += 1
    return {
        "message": "Hello from Rustlette!",
        "framework": "rustlette",
        "timestamp": time.time(),
    }


@app.route("/health")
async def health(request):
    """Health check endpoint."""
    return {"status": "ok", "framework": "rustlette"}


@app.route("/json")
async def json_response(request):
    """JSON response with more complex data."""
    stats["requests"] += 1
    return {
        "users": list(SAMPLE_USERS.values()),
        "total": len(SAMPLE_USERS),
        "generated_at": time.time(),
        "server": "rustlette",
    }


@app.route("/text")
async def text_response(request):
    """Plain text response."""
    stats["requests"] += 1
    return rustlette.Response(
        "Hello from Rustlette! This is a plain text response.",
        headers={"content-type": "text/plain"},
    )


@app.route("/users/{user_id:int}")
async def get_user(request):
    """Get user by ID with path parameter."""
    stats["requests"] += 1
    user_id = request.path_params["user_id"]

    if user_id not in SAMPLE_USERS:
        return rustlette.JSONResponse(
            {"error": "User not found", "user_id": user_id}, status_code=404
        )

    return SAMPLE_USERS[user_id]


@app.route("/search")
async def search_users(request):
    """Search endpoint with query parameters."""
    stats["requests"] += 1
    query = request.query_params.get("q", "")
    limit = int(request.query_params.get("limit", "10"))

    # Simple search simulation
    results = []
    for user in SAMPLE_USERS.values():
        if (
            query.lower() in user["name"].lower()
            or query.lower() in user["email"].lower()
        ):
            results.append(user)
        if len(results) >= limit:
            break

    return {
        "query": query,
        "results": results,
        "total": len(results),
        "limit": limit,
    }


@app.post("/users")
async def create_user(request):
    """Create user endpoint (POST with JSON body)."""
    stats["requests"] += 1

    try:
        user_data = await request.json()
    except:
        return rustlette.JSONResponse({"error": "Invalid JSON"}, status_code=400)

    # Simple validation
    if "name" not in user_data or "email" not in user_data:
        return rustlette.JSONResponse(
            {"error": "Name and email are required"}, status_code=400
        )

    # Simulate user creation
    new_id = max(SAMPLE_USERS.keys()) + 1 if SAMPLE_USERS else 1
    new_user = {
        "id": new_id,
        "name": user_data["name"],
        "email": user_data["email"],
        "active": user_data.get("active", True),
        "created_at": time.time(),
    }

    SAMPLE_USERS[new_id] = new_user

    return rustlette.JSONResponse(new_user, status_code=201)


@app.route("/echo", methods=["POST"])
async def echo(request):
    """Echo endpoint that returns the request body."""
    stats["requests"] += 1

    try:
        data = await request.json()
        return {
            "method": request.method,
            "echo": data,
            "timestamp": time.time(),
        }
    except:
        body = await request.body()
        return {
            "method": request.method,
            "echo": body.decode("utf-8") if body else "",
            "timestamp": time.time(),
        }


@app.route("/stats")
async def get_stats(request):
    """Get server statistics."""
    uptime = time.time() - stats["start_time"]
    return {
        "framework": "rustlette",
        "requests_served": stats["requests"],
        "uptime_seconds": uptime,
        "requests_per_second": stats["requests"] / uptime if uptime > 0 else 0,
        "rust_core_active": rustlette.get_status()["rust_core_available"],
    }


@app.route("/heavy")
async def heavy_computation(request):
    """Endpoint that does some computation to test CPU performance."""
    stats["requests"] += 1

    # Simple computation
    result = 0
    for i in range(10000):
        result += i * i

    return {
        "computation_result": result,
        "iterations": 10000,
        "framework": "rustlette",
    }


# Event handlers
@app.on_event("startup")
async def startup():
    print("Rustlette benchmark app starting...")
    stats["start_time"] = time.time()


@app.on_event("shutdown")
async def shutdown():
    print("Rustlette benchmark app shutting down...")
    print(f"Total requests served: {stats['requests']}")


if __name__ == "__main__":
    import uvicorn

    print("Starting Rustlette benchmark server...")
    uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False, log_level="warning")
