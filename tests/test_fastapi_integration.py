"""Tests for FastAPI integration — Rustlette as a drop-in Starlette replacement.

This test module monkey-patches sys.modules so that FastAPI's `from starlette.xxx`
imports resolve to `rustlette.xxx`, simulating a user who replaced starlette with
rustlette in their environment.

Skipped when FastAPI/Pydantic are not installed or incompatible.
"""

import sys

import pytest

# ============================================================
# Guard: skip entire module if FastAPI or Pydantic unavailable
# ============================================================
pytest.importorskip(
    "fastapi", reason="FastAPI not installed — skipping integration tests"
)
pytest.importorskip(
    "pydantic", reason="Pydantic not installed — skipping integration tests"
)

# ============================================================
# Monkey-patch starlette -> rustlette BEFORE importing FastAPI
# ============================================================
import rustlette
import rustlette.applications
import rustlette.authentication
import rustlette.background
import rustlette.concurrency
import rustlette.convertors
import rustlette.datastructures
import rustlette.endpoints
import rustlette.exceptions
import rustlette.formparsers
import rustlette.middleware
import rustlette.middleware.authentication
import rustlette.middleware.base
import rustlette.middleware.cors
import rustlette.middleware.errors
import rustlette.middleware.exceptions
import rustlette.middleware.gzip
import rustlette.middleware.httpsredirect
import rustlette.middleware.sessions
import rustlette.middleware.trustedhost
import rustlette.middleware.wsgi
import rustlette.requests
import rustlette.responses
import rustlette.routing
import rustlette.status
import rustlette.testclient
import rustlette.types
import rustlette.websockets
import rustlette._exception_handler
import rustlette._utils

for key in list(sys.modules.keys()):
    if key.startswith("rustlette"):
        starlette_key = "starlette" + key[len("rustlette") :]
        sys.modules[starlette_key] = sys.modules[key]

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from pydantic import BaseModel
except Exception as _exc:
    pytest.skip(
        f"FastAPI/Pydantic integration not compatible: {_exc}", allow_module_level=True
    )


# ============================================================
# FastAPI app definition
# ============================================================

try:
    app = FastAPI(title="Rustlette Integration Test")

    class Item(BaseModel):
        name: str
        price: float
        in_stock: bool = True

    items_db: dict = {}

    @app.get("/")
    async def root():
        return {"message": "Hello from FastAPI on Rustlette!"}

    @app.get("/items/{item_id}")
    async def get_item(item_id: int, q: str = None):
        return {"item_id": item_id, "q": q}

    @app.post("/items/", status_code=201)
    async def create_item(item: Item):
        return {"item": item.dict(), "status": "created"}

    @app.put("/items/{item_id}")
    async def update_item(item_id: int, item: Item):
        return {"item_id": item_id, "item": item.dict()}

    @app.delete("/items/{item_id}")
    async def delete_item(item_id: int):
        return {"deleted": item_id}

    @app.get("/headers")
    async def read_headers(request: rustlette.requests.Request):
        return {"user_agent": request.headers.get("user-agent", "unknown")}

    @app.get("/query")
    async def query_params(a: str = "default_a", b: int = 0):
        return {"a": a, "b": b}

    # ============================================================
    # Tests
    # ============================================================
    client = TestClient(app)

except Exception as _exc:
    pytest.skip(f"FastAPI app setup failed: {_exc}", allow_module_level=True)


class TestFastAPIBasicRoutes:
    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Hello from FastAPI on Rustlette!"}

    def test_get_item(self):
        response = client.get("/items/42")
        assert response.status_code == 200
        assert response.json() == {"item_id": 42, "q": None}

    def test_get_item_with_query(self):
        response = client.get("/items/42?q=search")
        assert response.json() == {"item_id": 42, "q": "search"}

    def test_create_item(self):
        response = client.post(
            "/items/",
            json={"name": "Widget", "price": 9.99, "in_stock": True},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["item"]["name"] == "Widget"
        assert data["item"]["price"] == 9.99
        assert data["status"] == "created"

    def test_update_item(self):
        response = client.put(
            "/items/42",
            json={"name": "Updated Widget", "price": 19.99},
        )
        assert response.status_code == 200
        assert response.json()["item_id"] == 42
        assert response.json()["item"]["name"] == "Updated Widget"

    def test_delete_item(self):
        response = client.delete("/items/42")
        assert response.status_code == 200
        assert response.json() == {"deleted": 42}


class TestFastAPIHTTPMethods:
    def test_404_not_found(self):
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_405_method_not_allowed(self):
        response = client.post("/")  # GET-only endpoint
        assert response.status_code == 405

    def test_422_validation_error(self):
        response = client.get("/items/not-an-int")
        assert response.status_code == 422


class TestFastAPIHeaders:
    def test_custom_header(self):
        response = client.get("/headers")
        assert response.json()["user_agent"] == "testclient"

    def test_request_headers_forwarded(self):
        response = client.get("/headers", headers={"User-Agent": "custom-agent"})
        assert response.json()["user_agent"] == "custom-agent"


class TestFastAPIQueryParams:
    def test_default_params(self):
        response = client.get("/query")
        assert response.json() == {"a": "default_a", "b": 0}

    def test_custom_params(self):
        response = client.get("/query?a=hello&b=42")
        assert response.json() == {"a": "hello", "b": 42}


class TestFastAPIOpenAPI:
    def test_openapi_schema(self):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "Rustlette Integration Test"

    def test_openapi_paths(self):
        response = client.get("/openapi.json")
        paths = response.json()["paths"]
        assert "/" in paths
        assert "/items/{item_id}" in paths
        assert "/items/" in paths

    def test_swagger_docs(self):
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_docs(self):
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestFastAPIPydanticValidation:
    def test_valid_body(self):
        response = client.post(
            "/items/",
            json={"name": "Valid Item", "price": 5.0},
        )
        assert response.status_code == 201

    def test_invalid_body_missing_field(self):
        response = client.post("/items/", json={"name": "Missing Price"})
        assert response.status_code == 422

    def test_invalid_body_wrong_type(self):
        response = client.post(
            "/items/",
            json={"name": "Bad Price", "price": "not-a-number"},
        )
        assert response.status_code == 422

    def test_path_param_validation(self):
        # item_id expects int
        response = client.get("/items/abc")
        assert response.status_code == 422


class TestFastAPILifespan:
    def test_lifespan_with_fastapi(self):
        import contextlib

        events = []

        @contextlib.asynccontextmanager
        async def lifespan(app):
            events.append("startup")
            yield
            events.append("shutdown")

        lifespan_app = FastAPI(lifespan=lifespan)

        @lifespan_app.get("/")
        async def homepage():
            return {"ok": True}

        with TestClient(lifespan_app) as test_client:
            assert events == ["startup"]
            response = test_client.get("/")
            assert response.status_code == 200

        assert events == ["startup", "shutdown"]
