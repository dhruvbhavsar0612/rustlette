"""
Advanced Rustlette application example

This example demonstrates advanced features of Rustlette including:
- Custom middleware for authentication and logging
- File upload handling
- Streaming responses
- WebSocket support (placeholder)
- Database integration patterns
- Advanced routing with sub-applications
- Custom error handling
- Rate limiting
- Caching patterns
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from rustlette import Rustlette, Request, Response, JSONResponse, PlainTextResponse
from rustlette.responses import FileResponse, StreamingResponse, HTMLResponse
from rustlette.background import BackgroundTasks
from rustlette.exceptions import HTTPException
from rustlette.middleware import BaseHTTPMiddleware, cors, trusted_host
from rustlette.routing import Mount, Router
from rustlette import status

# Create the main application
app = Rustlette(debug=True)

# Add trusted host middleware (security)
app.add_middleware(
    trusted_host(
        allowed_hosts=["localhost", "127.0.0.1", "*.example.com"],
        www_redirect=True,
    )
)

# Add CORS middleware
app.add_middleware(
    cors(
        allow_origins=["http://localhost:3000", "https://example.com"],
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
        allow_credentials=True,
    )
)

# Sample data stores
users_db = {}
sessions_db = {}
upload_dir = "uploads"
cache_store = {}

# Ensure upload directory exists
os.makedirs(upload_dir, exist_ok=True)


# Custom Authentication Middleware
class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Custom authentication middleware"""

    async def dispatch(self, request: Request, call_next):
        # Skip auth for public endpoints
        public_paths = ["/", "/health", "/login", "/register"]
        if request.path in public_paths:
            return await call_next(request)

        # Check for authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract and validate token
        token = auth_header.split(" ")[1]
        user = validate_token(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Add user to request state
        request.state["user"] = user
        return await call_next(request)


# Custom Logging Middleware
class LoggingMiddleware(BaseHTTPMiddleware):
    """Custom request logging middleware"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Log request
        print(f"Request: {request.method} {request.path}")

        response = await call_next(request)

        # Log response
        duration = time.time() - start_time
        print(f"Response: {response.status_code} ({duration:.3f}s)")

        # Add timing header
        response.headers["X-Process-Time"] = str(duration)

        return response


# Custom Rate Limiting Middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware"""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client[0] if request.client else "unknown"
        current_time = time.time()

        # Clean old entries
        cutoff_time = current_time - 60  # 1 minute ago
        self.request_counts = {
            ip: [
                (timestamp, count)
                for timestamp, count in requests
                if timestamp > cutoff_time
            ]
            for ip, requests in self.request_counts.items()
        }

        # Count requests for this IP
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []

        self.request_counts[client_ip].append((current_time, 1))

        # Check rate limit
        total_requests = sum(count for _, count in self.request_counts[client_ip])
        if total_requests > self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"},
            )

        return await call_next(request)


# Add custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
# Note: AuthenticationMiddleware would be added for protected routes


# Authentication helpers
def validate_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate JWT token (simplified)"""
    # In a real app, you'd use a proper JWT library
    if token in sessions_db:
        session = sessions_db[token]
        if session["expires"] > datetime.now():
            return session["user"]
    return None


def create_token(user: Dict[str, Any]) -> str:
    """Create a simple token (use JWT in production)"""
    import uuid

    token = str(uuid.uuid4())
    sessions_db[token] = {
        "user": user,
        "expires": datetime.now() + timedelta(hours=24),
    }
    return token


# Main routes
@app.route("/")
async def homepage(request: Request) -> HTMLResponse:
    """Advanced homepage with HTML response"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Advanced Rustlette App</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Advanced Rustlette Application</h1>
            <p>This is an advanced example showcasing various Rustlette features.</p>

            <h2>Available Endpoints:</h2>
            <div class="endpoint">GET /health - Health check</div>
            <div class="endpoint">POST /login - User authentication</div>
            <div class="endpoint">POST /upload - File upload</div>
            <div class="endpoint">GET /download/{filename} - File download</div>
            <div class="endpoint">GET /stream - Streaming response</div>
            <div class="endpoint">GET /cache/{key} - Cached data</div>
            <div class="endpoint">GET /admin/* - Admin panel (mounted app)</div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(html_content)


@app.route("/health")
async def health_check(request: Request) -> JSONResponse:
    """Enhanced health check with system info"""
    import psutil
    import sys

    return JSONResponse(
        {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "0.1.0",
            "python_version": sys.version,
            "memory_usage": psutil.virtual_memory().percent,
            "cpu_usage": psutil.cpu_percent(),
            "active_sessions": len(sessions_db),
        }
    )


@app.post("/login")
async def login(request: Request) -> JSONResponse:
    """User login endpoint"""
    try:
        credentials = await request.json()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON in request body",
        )

    username = credentials.get("username")
    password = credentials.get("password")

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required",
        )

    # Simple authentication (use proper password hashing in production)
    if username == "admin" and password == "secret":
        user = {"id": 1, "username": username, "role": "admin"}
        token = create_token(user)

        return JSONResponse(
            {
                "access_token": token,
                "token_type": "bearer",
                "user": user,
            }
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )


@app.post("/upload")
async def upload_file(request: Request) -> JSONResponse:
    """File upload endpoint"""
    content_type = request.headers.get("content-type", "")

    if not content_type.startswith("multipart/form-data"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expected multipart/form-data",
        )

    # Get the raw body (in a real app, you'd use a proper multipart parser)
    body = await request.body()

    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No file uploaded"
        )

    # Save file (simplified - use proper multipart parsing in production)
    import uuid

    filename = f"upload_{uuid.uuid4().hex[:8]}.bin"
    filepath = os.path.join(upload_dir, filename)

    with open(filepath, "wb") as f:
        f.write(body)

    # Add background task to process file
    background_tasks = BackgroundTasks()
    background_tasks.add_task(process_uploaded_file, filepath)

    return JSONResponse(
        {
            "filename": filename,
            "size": len(body),
            "path": f"/download/{filename}",
            "status": "uploaded",
        },
        status_code=status.HTTP_201_CREATED,
        background=background_tasks,
    )


@app.get("/download/{filename}")
async def download_file(request: Request) -> FileResponse:
    """File download endpoint"""
    filename = request.path_params["filename"]
    filepath = os.path.join(upload_dir, filename)

    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    return FileResponse(
        path=filepath, filename=filename, media_type="application/octet-stream"
    )


@app.get("/stream")
async def stream_data(request: Request) -> StreamingResponse:
    """Streaming response endpoint"""

    async def generate_data():
        """Generate streaming data"""
        for i in range(100):
            data = {
                "chunk": i,
                "timestamp": datetime.now().isoformat(),
                "data": f"This is chunk number {i}",
            }
            yield f"data: {json.dumps(data)}\n\n"

            # Simulate processing time
            import asyncio

            await asyncio.sleep(0.1)

    return StreamingResponse(
        generate_data(), media_type="text/plain", headers={"Cache-Control": "no-cache"}
    )


@app.route("/cache/{key}")
async def cached_data(request: Request) -> JSONResponse:
    """Cached data endpoint with TTL"""
    key = request.path_params["key"]
    current_time = time.time()

    # Check cache
    if key in cache_store:
        cache_entry = cache_store[key]
        if cache_entry["expires"] > current_time:
            return JSONResponse(
                {
                    "key": key,
                    "data": cache_entry["data"],
                    "cached": True,
                    "expires_in": cache_entry["expires"] - current_time,
                }
            )

    # Generate new data
    new_data = {
        "generated_at": datetime.now().isoformat(),
        "random_value": hash(key + str(current_time)) % 10000,
        "key": key,
    }

    # Cache for 5 minutes
    cache_store[key] = {
        "data": new_data,
        "expires": current_time + 300,
    }

    return JSONResponse(
        {
            "key": key,
            "data": new_data,
            "cached": False,
            "expires_in": 300,
        }
    )


@app.delete("/cache")
async def clear_cache(request: Request) -> JSONResponse:
    """Clear all cached data"""
    cleared_keys = list(cache_store.keys())
    cache_store.clear()

    return JSONResponse(
        {
            "message": "Cache cleared",
            "cleared_keys": cleared_keys,
            "count": len(cleared_keys),
        }
    )


# Background task functions
def process_uploaded_file(filepath: str) -> None:
    """Background task to process uploaded files"""
    print(f"Processing uploaded file: {filepath}")

    # Simulate file processing
    time.sleep(1)

    # Get file info
    file_size = os.path.getsize(filepath)
    print(f"File processed: {filepath} ({file_size} bytes)")


# Admin sub-application
admin_app = Rustlette()


@admin_app.route("/")
async def admin_dashboard(request: Request) -> JSONResponse:
    """Admin dashboard"""
    return JSONResponse(
        {
            "message": "Admin Dashboard",
            "stats": {
                "active_sessions": len(sessions_db),
                "cache_entries": len(cache_store),
                "upload_files": len(os.listdir(upload_dir))
                if os.path.exists(upload_dir)
                else 0,
            },
        }
    )


@admin_app.route("/users")
async def admin_users(request: Request) -> JSONResponse:
    """Admin user management"""
    return JSONResponse(
        {
            "users": list(users_db.values()),
            "total": len(users_db),
        }
    )


@admin_app.route("/sessions")
async def admin_sessions(request: Request) -> JSONResponse:
    """Admin session management"""
    active_sessions = [
        {
            "token": token[:8] + "...",
            "user": session["user"]["username"],
            "expires": session["expires"].isoformat(),
        }
        for token, session in sessions_db.items()
        if session["expires"] > datetime.now()
    ]

    return JSONResponse(
        {
            "active_sessions": active_sessions,
            "total": len(active_sessions),
        }
    )


# Mount admin sub-application
app.mount("/admin", admin_app, name="admin")


# API v1 sub-application
api_v1 = Router()


@api_v1.route("/info")
async def api_info(request: Request) -> JSONResponse:
    """API information"""
    return JSONResponse(
        {
            "version": "1.0",
            "name": "Rustlette Advanced API",
            "endpoints": [
                "/api/v1/info",
                "/api/v1/stats",
            ],
        }
    )


@api_v1.route("/stats")
async def api_stats(request: Request) -> JSONResponse:
    """API statistics"""
    return JSONResponse(
        {
            "requests_served": 12345,  # Would be tracked in real app
            "uptime": "5d 3h 42m",
            "performance": {
                "avg_response_time": "15ms",
                "requests_per_second": 100,
            },
        }
    )


# Mount API router
app.mount("/api/v1", api_v1, name="api_v1")


# WebSocket endpoint (placeholder)
@app.websocket_route("/ws")
async def websocket_endpoint(websocket):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()

    try:
        while True:
            # Echo messages back
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    print("Advanced Rustlette application starting up...")
    print(f"Upload directory: {upload_dir}")

    # Initialize some demo data
    users_db[1] = {"id": 1, "username": "admin", "email": "admin@example.com"}

    # Warm up cache
    cache_store["demo"] = {
        "data": {"message": "Demo cache entry"},
        "expires": time.time() + 3600,
    }


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    print("Advanced Rustlette application shutting down...")
    print(
        f"Final stats - Users: {len(users_db)}, Sessions: {len(sessions_db)}, Cache: {len(cache_store)}"
    )


# Custom exception handlers
@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(
    request: Request, exc: FileNotFoundError
) -> JSONResponse:
    """Handle file not found errors"""
    return JSONResponse(
        content={
            "error": "FileNotFoundError",
            "message": "The requested file was not found",
            "path": request.path,
        },
        status_code=status.HTTP_404_NOT_FOUND,
    )


@app.exception_handler(PermissionError)
async def permission_error_handler(
    request: Request, exc: PermissionError
) -> JSONResponse:
    """Handle permission errors"""
    return JSONResponse(
        content={
            "error": "PermissionError",
            "message": "Permission denied",
            "path": request.path,
        },
        status_code=status.HTTP_403_FORBIDDEN,
    )


if __name__ == "__main__":
    # For development - use uvicorn for production
    import uvicorn

    uvicorn.run(
        "advanced_app:app",
        host="127.0.0.1",
        port=8001,
        reload=True,
        log_level="info",
        access_log=True,
    )
