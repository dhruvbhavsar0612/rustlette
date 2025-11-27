"""
Basic Rustlette application example

This example demonstrates the core features of Rustlette including:
- Basic routing with different HTTP methods
- Path parameters with type conversion
- JSON responses
- Middleware usage
- Background tasks
- Exception handling
"""

from rustlette import Rustlette, Request, Response, JSONResponse, PlainTextResponse
from rustlette.background import BackgroundTasks
from rustlette.exceptions import HTTPException
from rustlette.middleware import cors
from rustlette import status

# Create the application
app = Rustlette(debug=True)

# Add CORS middleware
app.add_middleware(
    cors(
        allow_origins=["*"],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
)

# Sample data store (in production, use a real database)
users_db = {
    1: {"id": 1, "name": "Alice", "email": "alice@example.com"},
    2: {"id": 2, "name": "Bob", "email": "bob@example.com"},
}
next_user_id = 3


@app.route("/")
async def homepage(request: Request) -> JSONResponse:
    """Homepage endpoint"""
    return JSONResponse(
        {
            "message": "Welcome to Rustlette!",
            "version": "0.1.0",
            "framework": "Rustlette with Rust internals",
        }
    )


@app.route("/health")
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint"""
    return JSONResponse({"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"})


@app.get("/users")
async def list_users(request: Request) -> JSONResponse:
    """Get all users"""
    return JSONResponse(list(users_db.values()))


@app.get("/users/{user_id:int}")
async def get_user(request: Request) -> JSONResponse:
    """Get a specific user by ID"""
    user_id = request.path_params["user_id"]

    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    return JSONResponse(users_db[user_id])


@app.post("/users")
async def create_user(request: Request) -> JSONResponse:
    """Create a new user"""
    global next_user_id

    try:
        user_data = await request.json()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON in request body",
        )

    # Validate required fields
    if "name" not in user_data or "email" not in user_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name and email are required",
        )

    # Create new user
    new_user = {
        "id": next_user_id,
        "name": user_data["name"],
        "email": user_data["email"],
    }

    users_db[next_user_id] = new_user
    next_user_id += 1

    # Add background task to log user creation
    background_tasks = BackgroundTasks()
    background_tasks.add_task(
        log_user_creation, user_id=new_user["id"], user_name=new_user["name"]
    )

    return JSONResponse(
        content=new_user,
        status_code=status.HTTP_201_CREATED,
        background=background_tasks,
    )


@app.put("/users/{user_id:int}")
async def update_user(request: Request) -> JSONResponse:
    """Update an existing user"""
    user_id = request.path_params["user_id"]

    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    try:
        user_data = await request.json()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON in request body",
        )

    # Update user
    user = users_db[user_id]
    user.update(user_data)

    return JSONResponse(user)


@app.delete("/users/{user_id:int}")
async def delete_user(request: Request) -> Response:
    """Delete a user"""
    user_id = request.path_params["user_id"]

    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    del users_db[user_id]

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.route("/search")
async def search_users(request: Request) -> JSONResponse:
    """Search users by name"""
    query = request.query_params.get("q", "").lower()

    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'q' is required",
        )

    # Filter users by name
    matching_users = [
        user for user in users_db.values() if query in user["name"].lower()
    ]

    return JSONResponse(
        {"query": query, "results": matching_users, "count": len(matching_users)}
    )


@app.route("/echo", methods=["POST"])
async def echo(request: Request) -> JSONResponse:
    """Echo back the request data"""
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        data = await request.json()
        response_data = {"type": "json", "data": data}
    else:
        body = await request.body()
        response_data = {"type": "text", "data": body.decode("utf-8") if body else ""}

    return JSONResponse(
        {
            "method": request.method,
            "path": request.path,
            "headers": dict(request.headers),
            "query_params": dict(request.query_params),
            "body": response_data,
        }
    )


@app.route("/slow")
async def slow_endpoint(request: Request) -> JSONResponse:
    """Endpoint that simulates slow processing"""
    import asyncio

    # Simulate slow processing
    await asyncio.sleep(2)

    return JSONResponse(
        {"message": "This was a slow endpoint", "processing_time": "2 seconds"}
    )


@app.route("/error")
async def trigger_error(request: Request) -> JSONResponse:
    """Endpoint that triggers an error for testing"""
    error_type = request.query_params.get("type", "generic")

    if error_type == "400":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bad request triggered")
    elif error_type == "404":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resource not found")
    elif error_type == "500":
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Server error triggered"
        )
    else:
        # Generic Python exception
        raise ValueError("This is a test error")


# Background task functions
def log_user_creation(user_id: int, user_name: str) -> None:
    """Background task to log user creation"""
    print(f"User created: ID={user_id}, Name={user_name}")


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    print("Rustlette application starting up...")
    print(f"Initial users: {len(users_db)}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    print("Rustlette application shutting down...")
    print(f"Final users: {len(users_db)}")


# Custom exception handler
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle ValueError exceptions"""
    return JSONResponse(
        content={"error": "ValueError", "message": str(exc), "path": request.path},
        status_code=status.HTTP_400_BAD_REQUEST,
    )


if __name__ == "__main__":
    # For development - use uvicorn for production
    import uvicorn

    uvicorn.run(
        "basic_app:app", host="127.0.0.1", port=8000, reload=True, log_level="info"
    )
