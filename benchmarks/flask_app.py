#!/usr/bin/env python3
"""
Flask benchmark application.

This creates a standard set of endpoints for benchmarking Flask
against other Python web frameworks.
"""

from flask import Flask, jsonify, request
import time
import json
from typing import Dict, Any

# Create the Flask application
app = Flask(__name__)

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
def root():
    """Simple JSON response endpoint."""
    stats["requests"] += 1
    return jsonify(
        {
            "message": "Hello from Flask!",
            "framework": "flask",
            "timestamp": time.time(),
        }
    )


@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "framework": "flask"})


@app.route("/json")
def json_response():
    """JSON response with more complex data."""
    stats["requests"] += 1
    return jsonify(
        {
            "users": list(SAMPLE_USERS.values()),
            "total": len(SAMPLE_USERS),
            "generated_at": time.time(),
            "server": "flask",
        }
    )


@app.route("/text")
def text_response():
    """Plain text response."""
    stats["requests"] += 1
    return (
        "Hello from Flask! This is a plain text response.",
        200,
        {"Content-Type": "text/plain"},
    )


@app.route("/users/<int:user_id>")
def get_user(user_id):
    """Get user by ID with path parameter."""
    stats["requests"] += 1

    if user_id not in SAMPLE_USERS:
        return jsonify({"error": "User not found", "user_id": user_id}), 404

    return jsonify(SAMPLE_USERS[user_id])


@app.route("/search")
def search_users():
    """Search endpoint with query parameters."""
    stats["requests"] += 1
    q = request.args.get("q", "")
    limit = int(request.args.get("limit", "10"))

    # Simple search simulation
    results = []
    for user in SAMPLE_USERS.values():
        if q.lower() in user["name"].lower() or q.lower() in user["email"].lower():
            results.append(user)
        if len(results) >= limit:
            break

    return jsonify(
        {
            "query": q,
            "results": results,
            "total": len(results),
            "limit": limit,
        }
    )


@app.route("/users", methods=["POST"])
def create_user():
    """Create user endpoint (POST with JSON body)."""
    stats["requests"] += 1

    try:
        user_data = request.get_json()
        if not user_data:
            raise ValueError("No JSON data")
    except:
        return jsonify({"error": "Invalid JSON"}), 400

    # Simple validation
    if "name" not in user_data or "email" not in user_data:
        return jsonify({"error": "Name and email are required"}), 400

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

    return jsonify(new_user), 201


@app.route("/echo", methods=["POST"])
def echo():
    """Echo endpoint that returns the request body."""
    stats["requests"] += 1

    try:
        data = request.get_json()
        return jsonify(
            {
                "method": request.method,
                "echo": data,
                "timestamp": time.time(),
            }
        )
    except:
        body = request.get_data(as_text=True)
        return jsonify(
            {
                "method": request.method,
                "echo": body,
                "timestamp": time.time(),
            }
        )


@app.route("/stats")
def get_stats():
    """Get server statistics."""
    uptime = time.time() - stats["start_time"]
    return jsonify(
        {
            "framework": "flask",
            "requests_served": stats["requests"],
            "uptime_seconds": uptime,
            "requests_per_second": stats["requests"] / uptime if uptime > 0 else 0,
        }
    )


@app.route("/heavy")
def heavy_computation():
    """Endpoint that does some computation to test CPU performance."""
    stats["requests"] += 1

    # Simple computation
    result = 0
    for i in range(10000):
        result += i * i

    return jsonify(
        {
            "computation_result": result,
            "iterations": 10000,
            "framework": "flask",
        }
    )


# Startup message
print("Flask benchmark app starting...")
stats["start_time"] = time.time()


if __name__ == "__main__":
    print("Starting Flask benchmark server...")
    app.run(host="127.0.0.1", port=8003, debug=False, threaded=True)
