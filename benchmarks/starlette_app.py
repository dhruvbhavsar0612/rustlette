#!/usr/bin/env python3
"""
Starlette benchmark application.

This creates a standard set of endpoints for benchmarking Starlette
against other Python web frameworks.
"""

from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.middleware import Middleware
import time
import json
from typing import Dict, Any

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


async def root(request):
    """Simple JSON response endpoint."""
    stats["requests"] += 1
    return JSONResponse(
        {
            "message": "Hello from Starlette!",
            "framework": "starlette",
            "timestamp": time.time(),
        }
    )


async def health(request):
    """Health check endpoint."""
    return JSONResponse({"status": "ok", "framework": "starlette"})


async def json_response(request):
    """JSON response with more complex data."""
    stats["requests"] += 1
    return JSONResponse(
        {
            "users": list(SAMPLE_USERS.values()),
            "total": len(SAMPLE_USERS),
            "generated_at": time.time(),
            "server": "starlette",
        }
    )


async def text_response(request):
    """Plain text response."""
    stats["requests"] += 1
    return PlainTextResponse("Hello from Starlette! This is a plain text response.")


async def get_user(request):
    """Get user by ID with path parameter."""
    stats["requests"] += 1
    user_id = int(request.path_params["user_id"])

    if user_id not in SAMPLE_USERS:
        return JSONResponse(
            {"error": "User not found", "user_id": user_id}, status_code=404
        )

    return JSONResponse(SAMPLE_USERS[user_id])


async def search_users(request):
    """Search endpoint with query parameters."""
    stats["requests"] += 1
    query_params = request.query_params
    q = query_params.get("q", "")
    limit = int(query_params.get("limit", "10"))

    # Simple search simulation
    results = []
    for user in SAMPLE_USERS.values():
        if q.lower() in user["name"].lower() or q.lower() in user["email"].lower():
            results.append(user)
        if len(results) >= limit:
            break

    return JSONResponse(
        {
            "query": q,
            "results": results,
            "total": len(results),
            "limit": limit,
        }
    )


async def create_user(request):
    """Create user endpoint (POST with JSON body)."""
    stats["requests"] += 1

    try:
        user_data = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    # Simple validation
    if "name" not in user_data or "email" not in user_data:
        return JSONResponse({"error": "Name and email are required"}, status_code=400)

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

    return JSONResponse(new_user, status_code=201)


async def echo(request):
    """Echo endpoint that returns the request body."""
    stats["requests"] += 1

    try:
        data = await request.json()
        return JSONResponse(
            {
                "method": request.method,
                "echo": data,
                "timestamp": time.time(),
            }
        )
    except:
        body = await request.body()
        return JSONResponse(
            {
                "method": request.method,
                "echo": body.decode("utf-8") if body else "",
                "timestamp": time.time(),
            }
        )


async def get_stats(request):
    """Get server statistics."""
    uptime = time.time() - stats["start_time"]
    return JSONResponse(
        {
            "framework": "starlette",
            "requests_served": stats["requests"],
            "uptime_seconds": uptime,
            "requests_per_second": stats["requests"] / uptime if uptime > 0 else 0,
        }
    )


async def heavy_computation(request):
    """Endpoint that does some computation to test CPU performance."""
    stats["requests"] += 1

    # Simple computation
    result = 0
    for i in range(10000):
        result += i * i

    return JSONResponse(
        {
            "computation_result": result,
            "iterations": 10000,
            "framework": "starlette",
        }
    )


# Event handlers
async def startup():
    print("Starlette benchmark app starting...")
    stats["start_time"] = time.time()


async def shutdown():
    print("Starlette benchmark app shutting down...")
    print(f"Total requests served: {stats['requests']}")


# Define routes
routes = [
    Route("/", root, methods=["GET"]),
    Route("/health", health, methods=["GET"]),
    Route("/json", json_response, methods=["GET"]),
    Route("/text", text_response, methods=["GET"]),
    Route("/users/{user_id:int}", get_user, methods=["GET"]),
    Route("/search", search_users, methods=["GET"]),
    Route("/users", create_user, methods=["POST"]),
    Route("/echo", echo, methods=["POST"]),
    Route("/stats", get_stats, methods=["GET"]),
    Route("/heavy", heavy_computation, methods=["GET"]),
]

# Create the Starlette application
app = Starlette(
    debug=False,
    routes=routes,
    on_startup=[startup],
    on_shutdown=[shutdown],
)

if __name__ == "__main__":
    import uvicorn

    print("Starting Starlette benchmark server...")
    uvicorn.run(app, host="127.0.0.1", port=8002, access_log=False, log_level="warning")
