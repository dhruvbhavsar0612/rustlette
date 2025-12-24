//! Main application class for Rustlette
//!
//! This module implements the core Rustlette application that provides a
//! Starlette-compatible API while leveraging Rust internals for performance.

use crate::asgi::{asgi_helpers, ASGIApp};
use crate::background::BackgroundTaskManager;
use crate::error::{RustletteError, RustletteResult};
use crate::middleware::MiddlewareStack;
use crate::request::RustletteRequest;
use crate::response::{
    HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, RustletteResponse,
};
use crate::routing::{Route, RouteMatch, Router};
use crate::types::{HTTPMethod, Headers, StatusCode};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

/// Lifecycle event types
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LifecycleEvent {
    Startup,
    Shutdown,
}

/// Event handler function
#[derive(Debug, Clone)]
pub struct EventHandler {
    pub event: LifecycleEvent,
    pub handler: PyObject,
}

impl EventHandler {
    pub fn new(event: LifecycleEvent, handler: PyObject) -> Self {
        Self { event, handler }
    }

    pub async fn execute(&self) -> PyResult<()> {
        Python::with_gil(|py| {
            let result = self.handler.call0(py)?;

            // If it's a coroutine, we should await it
            // For now, we'll just handle synchronous functions
            Ok(())
        })
    }
}

/// Exception handler function
#[derive(Debug, Clone)]
pub struct ExceptionHandler {
    pub exception_class: PyObject,
    pub handler: PyObject,
}

impl ExceptionHandler {
    pub fn new(exception_class: PyObject, handler: PyObject) -> Self {
        Self {
            exception_class,
            handler,
        }
    }

    pub fn can_handle(&self, exception: &RustletteError) -> bool {
        // For now, we'll do a simple check
        // In a full implementation, this would check if the exception matches the class
        true
    }

    pub async fn handle(
        &self,
        request: &RustletteRequest,
        exception: &RustletteError,
    ) -> PyResult<RustletteResponse> {
        Python::with_gil(|py| {
            let req_py = Py::new(py, request.clone())?;
            let result = self.handler.call1(py, (req_py, exception.clone()))?;
            result.extract::<RustletteResponse>(py)
        })
    }
}

/// Main Rustlette application class
#[pyclass]
pub struct RustletteApp {
    router: Arc<RwLock<Router>>,
    middleware_stack: Arc<RwLock<MiddlewareStack>>,
    event_handlers: Arc<RwLock<Vec<EventHandler>>>,
    exception_handlers: Arc<RwLock<Vec<ExceptionHandler>>>,
    background_manager: Arc<BackgroundTaskManager>,
    debug: bool,
    state: Arc<RwLock<HashMap<String, PyObject>>>,
}

#[pymethods]
impl RustletteApp {
    #[new]
    #[pyo3(signature = (debug=false, routes=None, middleware=None))]
    pub fn new(
        debug: Option<bool>,
        routes: Option<&PyList>,
        middleware: Option<&PyList>,
    ) -> PyResult<Self> {
        let mut router = Router::new();
        let mut middleware_stack = MiddlewareStack::new();

        // Add provided routes
        if let Some(routes_list) = routes {
            for route_obj in routes_list.iter() {
                let route: Route = route_obj.extract()?;
                router.add_route(route)?;
            }
        }

        // Add provided middleware
        if let Some(middleware_list) = middleware {
            for middleware_obj in middleware_list.iter() {
                let middleware = crate::middleware::Middleware::new(middleware_obj.into(), None);
                middleware_stack.add(middleware);
            }
        }

        Ok(Self {
            router: Arc::new(RwLock::new(router)),
            middleware_stack: Arc::new(RwLock::new(middleware_stack)),
            event_handlers: Arc::new(RwLock::new(Vec::new())),
            exception_handlers: Arc::new(RwLock::new(Vec::new())),
            background_manager: Arc::new(BackgroundTaskManager::new(Some(4))),
            debug: debug.unwrap_or(false),
            state: Arc::new(RwLock::new(HashMap::new())),
        })
    }

    /// Add a route to the application
    pub fn add_route<'py>(
        &self,
        py: Python<'py>,
        path: String,
        endpoint: PyObject,
        methods: Option<Vec<String>>,
        name: Option<String>,
        include_in_schema: Option<bool>,
    ) -> PyResult<&'py PyAny> {
        let route = Route::new(path, Some(endpoint), methods, name, include_in_schema)?;
        let router = self.router.clone();

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let mut router = router.write().await;
            router.add_route(route)?;
            Ok(())
        })
    }

    /// Add a GET route
    #[pyo3(signature = (path, endpoint, name=None, include_in_schema=None))]
    pub fn get<'py>(
        &self,
        py: Python<'py>,
        path: String,
        endpoint: PyObject,
        name: Option<String>,
        include_in_schema: Option<bool>,
    ) -> PyResult<&'py PyAny> {
        self.add_route(
            py,
            path,
            endpoint,
            Some(vec!["GET".to_string()]),
            name,
            include_in_schema,
        )
    }

    /// Add a POST route
    #[pyo3(signature = (path, endpoint, name=None, include_in_schema=None))]
    pub fn post<'py>(
        &self,
        py: Python<'py>,
        path: String,
        endpoint: PyObject,
        name: Option<String>,
        include_in_schema: Option<bool>,
    ) -> PyResult<&'py PyAny> {
        self.add_route(
            py,
            path,
            endpoint,
            Some(vec!["POST".to_string()]),
            name,
            include_in_schema,
        )
    }

    /// Add a PUT route
    #[pyo3(signature = (path, endpoint, name=None, include_in_schema=None))]
    pub fn put<'py>(
        &self,
        py: Python<'py>,
        path: String,
        endpoint: PyObject,
        name: Option<String>,
        include_in_schema: Option<bool>,
    ) -> PyResult<&'py PyAny> {
        self.add_route(
            py,
            path,
            endpoint,
            Some(vec!["PUT".to_string()]),
            name,
            include_in_schema,
        )
    }

    /// Add a DELETE route
    #[pyo3(signature = (path, endpoint, name=None, include_in_schema=None))]
    pub fn delete<'py>(
        &self,
        py: Python<'py>,
        path: String,
        endpoint: PyObject,
        name: Option<String>,
        include_in_schema: Option<bool>,
    ) -> PyResult<&'py PyAny> {
        self.add_route(
            py,
            path,
            endpoint,
            Some(vec!["DELETE".to_string()]),
            name,
            include_in_schema,
        )
    }

    /// Add a PATCH route
    #[pyo3(signature = (path, endpoint, name=None, include_in_schema=None))]
    pub fn patch<'py>(
        &self,
        py: Python<'py>,
        path: String,
        endpoint: PyObject,
        name: Option<String>,
        include_in_schema: Option<bool>,
    ) -> PyResult<&'py PyAny> {
        self.add_route(
            py,
            path,
            endpoint,
            Some(vec!["PATCH".to_string()]),
            name,
            include_in_schema,
        )
    }

    /// Add a HEAD route
    #[pyo3(signature = (path, endpoint, name=None, include_in_schema=None))]
    pub fn head<'py>(
        &self,
        py: Python<'py>,
        path: String,
        endpoint: PyObject,
        name: Option<String>,
        include_in_schema: Option<bool>,
    ) -> PyResult<&'py PyAny> {
        self.add_route(
            py,
            path,
            endpoint,
            Some(vec!["HEAD".to_string()]),
            name,
            include_in_schema,
        )
    }

    /// Add an OPTIONS route
    #[pyo3(signature = (path, endpoint, name=None, include_in_schema=None))]
    pub fn options<'py>(
        &self,
        py: Python<'py>,
        path: String,
        endpoint: PyObject,
        name: Option<String>,
        include_in_schema: Option<bool>,
    ) -> PyResult<&'py PyAny> {
        self.add_route(
            py,
            path,
            endpoint,
            Some(vec!["OPTIONS".to_string()]),
            name,
            include_in_schema,
        )
    }

    /// Add middleware to the application
    pub fn add_middleware<'py>(
        &self,
        py: Python<'py>,
        middleware: PyObject,
        name: Option<String>,
    ) -> PyResult<&'py PyAny> {
        let middleware = crate::middleware::Middleware::new(middleware, name);
        let middleware_stack = self.middleware_stack.clone();

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let mut stack = middleware_stack.write().await;
            stack.add(middleware);
            Ok(())
        })
    }

    /// Add an event handler for startup or shutdown
    pub fn add_event_handler<'py>(
        &self,
        py: Python<'py>,
        event: String,
        handler: PyObject,
    ) -> PyResult<&'py PyAny> {
        let event_type = match event.to_lowercase().as_str() {
            "startup" => LifecycleEvent::Startup,
            "shutdown" => LifecycleEvent::Shutdown,
            _ => {
                return Err(pyo3::exceptions::PyValueError::new_err(format!(
                    "Unknown event type: {}. Must be 'startup' or 'shutdown'",
                    event
                )))
            }
        };

        let event_handler = EventHandler::new(event_type, handler);
        let event_handlers = self.event_handlers.clone();

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let mut handlers = event_handlers.write().await;
            handlers.push(event_handler);
            Ok(())
        })
    }

    /// Add an exception handler
    pub fn add_exception_handler<'py>(
        &self,
        py: Python<'py>,
        exception_class: PyObject,
        handler: PyObject,
    ) -> PyResult<&'py PyAny> {
        let exception_handler = ExceptionHandler::new(exception_class, handler);
        let exception_handlers = self.exception_handlers.clone();

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let mut handlers = exception_handlers.write().await;
            handlers.push(exception_handler);
            Ok(())
        })
    }

    /// Mount a sub-application at a given path
    pub fn mount<'py>(
        &self,
        py: Python<'py>,
        path: String,
        app: PyObject,
        name: Option<String>,
    ) -> PyResult<&'py PyAny> {
        // For now, we'll just add this as a catch-all route
        // In a full implementation, this would handle sub-application mounting
        self.add_route(
            py,
            format!("{}{{path:path}}", path.trim_end_matches('/')),
            app,
            None,
            name,
            Some(false),
        )
    }

    /// Generate URL for a named route
    pub fn url_path_for<'py>(
        &self,
        py: Python<'py>,
        name: String,
        path_params: Option<HashMap<String, PyObject>>,
    ) -> PyResult<&'py PyAny> {
        let router = self.router.clone();

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let router = router.read().await;
            router
                .url_for(&name, path_params)
                .map_err(|e| pyo3::exceptions::PyKeyError::new_err(e.to_string()))
        })
    }

    /// Process a request through the application
    #[pyo3(name = "__call__")]
    pub fn call<'py>(&self, py: Python<'py>, request: RustletteRequest) -> PyResult<&'py PyAny> {
        let app_clone = self.clone();
        pyo3_asyncio::tokio::future_into_py(
            py,
            async move { app_clone.process_request(request).await },
        )
    }

    /// Get application state
    pub fn get_state<'py>(&self, py: Python<'py>, key: String) -> PyResult<&'py PyAny> {
        let state = self.state.clone();

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let state = state.read().await;
            Ok(state.get(&key).cloned())
        })
    }

    /// Set application state
    pub fn set_state<'py>(
        &self,
        py: Python<'py>,
        key: String,
        value: PyObject,
    ) -> PyResult<&'py PyAny> {
        let state = self.state.clone();

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let mut state = state.write().await;
            state.insert(key, value);
            Ok(())
        })
    }

    /// Get debug mode
    #[getter]
    pub fn debug(&self) -> bool {
        self.debug
    }

    /// Set debug mode
    #[setter]
    pub fn set_debug(&mut self, debug: bool) {
        self.debug = debug;
    }

    /// Create an ASGI application
    pub fn asgi(&self) -> ASGIApp {
        let app_obj = Python::with_gil(|py| self.clone().into_py(py));
        ASGIApp::new(app_obj)
    }

    /// Route decorator
    #[pyo3(signature = (path, methods=None, name=None, include_in_schema=None))]
    pub fn route(
        &self,
        path: String,
        methods: Option<Vec<String>>,
        name: Option<String>,
        include_in_schema: Option<bool>,
    ) -> PyResult<PyObject> {
        let app_clone = self.clone();

        Python::with_gil(|py| {
            let decorator = py.eval(
                r#"
def decorator(func):
    app.add_route(path, func, methods, name, include_in_schema)
    return func
"#,
                None,
                Some(
                    [
                        ("app", app_clone.into_py(py)),
                        ("path", path.into_py(py)),
                        ("methods", methods.into_py(py)),
                        ("name", name.into_py(py)),
                        ("include_in_schema", include_in_schema.into_py(py)),
                    ]
                    .into_iter()
                    .collect::<HashMap<&str, PyObject>>()
                    .into_py(py)
                    .downcast::<PyDict>(py)
                    .unwrap(),
                ),
            )?;

            Ok(decorator.into())
        })
    }

    fn __repr__(&self) -> String {
        format!("RustletteApp(debug={})", self.debug)
    }
}

impl Clone for RustletteApp {
    fn clone(&self) -> Self {
        Self {
            router: Arc::clone(&self.router),
            middleware_stack: Arc::clone(&self.middleware_stack),
            event_handlers: Arc::clone(&self.event_handlers),
            exception_handlers: Arc::clone(&self.exception_handlers),
            background_manager: Arc::clone(&self.background_manager),
            debug: self.debug,
            state: Arc::clone(&self.state),
        }
    }
}

impl RustletteApp {
    /// Process a request through the entire application stack
    pub async fn process_request(
        &self,
        mut request: RustletteRequest,
    ) -> PyResult<RustletteResponse> {
        // Process through middleware stack
        {
            let middleware = self.middleware_stack.read().await;
            if let Err(e) = middleware.process_request(&mut request).await {
                return self.handle_exception(&request, &e).await;
            }
        }

        // Route the request
        let route_match = {
            let router = self.router.read().await;
            let path = request.path().map_err(|e| {
                RustletteError::internal_error(format!("Failed to get request path: {}", e))
            })?;
            router.match_request(&path, &request.method.to_string())
        };

        let mut response = if let Some(route_match) = route_match {
            // Set path parameters on request
            request.set_path_params(route_match.path_params.clone());

            // Call the route handler
            match self.call_endpoint(&request, &route_match).await {
                Ok(response) => response,
                Err(e) => {
                    let rustlette_error = RustletteError::internal_error(e.to_string());
                    return self.handle_exception(&request, &rustlette_error).await;
                }
            }
        } else {
            // No route found
            let error = RustletteError::not_found("Route not found");
            return self.handle_exception(&request, &error).await;
        };

        // Process through middleware stack (response)
        {
            let middleware = self.middleware_stack.read().await;
            if let Err(e) = middleware.process_response(&request, &mut response).await {
                return self.handle_exception(&request, &e).await;
            }
        }

        Ok(response)
    }

    /// Call a route endpoint
    async fn call_endpoint(
        &self,
        request: &RustletteRequest,
        route_match: &RouteMatch,
    ) -> PyResult<RustletteResponse> {
        Python::with_gil(|py| {
            if let Some(ref handler) = route_match.route.handler {
                let req_py = Py::new(py, request.clone())?;
                let result = handler.call1(py, (req_py,))?;

                // Handle different return types
                if let Ok(response) = result.extract::<RustletteResponse>(py) {
                    Ok(response)
                } else if let Ok(json_response) = result.extract::<JSONResponse>(py) {
                    // Extract the base response from JSONResponse
                    Ok(RustletteResponse::new(
                        Some(result),
                        Some(200),
                        None,
                        Some("application/json".to_string()),
                        None,
                    )?)
                } else if let Ok(string_result) = result.extract::<String>(py) {
                    // String response
                    RustletteResponse::new(
                        Some(string_result.into_py(py)),
                        Some(200),
                        None,
                        Some("text/plain".to_string()),
                        None,
                    )
                } else if let Ok(dict_result) = result.downcast::<PyDict>(py) {
                    // Dict response -> JSON
                    RustletteResponse::new(
                        Some(dict_result.into()),
                        Some(200),
                        None,
                        Some("application/json".to_string()),
                        None,
                    )
                } else {
                    // Try to convert to string
                    let string_repr = result.call_method0(py, "__str__")?.extract::<String>(py)?;
                    RustletteResponse::new(
                        Some(string_repr.into_py(py)),
                        Some(200),
                        None,
                        Some("text/plain".to_string()),
                        None,
                    )
                }
            } else {
                Err(pyo3::exceptions::PyRuntimeError::new_err(
                    "Route has no handler",
                ))
            }
        })
    }

    /// Handle exceptions through exception handlers or create default response
    async fn handle_exception(
        &self,
        request: &RustletteRequest,
        error: &RustletteError,
    ) -> PyResult<RustletteResponse> {
        // Try exception handlers first
        {
            let handlers = self.exception_handlers.read().await;
            for handler in handlers.iter() {
                if handler.can_handle(error) {
                    if let Ok(response) = handler.handle(request, error).await {
                        return Ok(response);
                    }
                }
            }
        }

        // Create default error response
        let status_code = error.status_code.unwrap_or(500);
        let error_message = if self.debug {
            error.message.clone()
        } else {
            match status_code {
                404 => "Not Found".to_string(),
                405 => "Method Not Allowed".to_string(),
                500 => "Internal Server Error".to_string(),
                _ => "Error".to_string(),
            }
        };

        Python::with_gil(|py| {
            RustletteResponse::new(
                Some(error_message.into_py(py)),
                Some(status_code),
                None,
                Some("text/plain".to_string()),
                None,
            )
        })
    }

    /// Run startup event handlers
    pub async fn startup(&self) -> RustletteResult<()> {
        let handlers = self.event_handlers.read().await;
        for handler in handlers.iter() {
            if handler.event == LifecycleEvent::Startup {
                handler.execute().await.map_err(|e| {
                    RustletteError::internal_error(format!("Startup handler failed: {}", e))
                })?;
            }
        }

        // Start background task manager
        // TODO: Fix lifetime issues with async start
        // Python::with_gil(|py| {
        //     self.background_manager.start(py)
        // })?;

        Ok(())
    }

    /// Run shutdown event handlers
    pub async fn shutdown(&self) -> RustletteResult<()> {
        let handlers = self.event_handlers.read().await;
        for handler in handlers.iter() {
            if handler.event == LifecycleEvent::Shutdown {
                handler.execute().await.map_err(|e| {
                    RustletteError::internal_error(format!("Shutdown handler failed: {}", e))
                })?;
            }
        }

        // Stop background task manager
        // TODO: Fix lifetime issues with async stop
        // Python::with_gil(|py| {
        //     self.background_manager.stop(py)
        // })?;

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_app_creation() {
        Python::with_gil(|py| {
            let app = RustletteApp::new(Some(true), None, None).unwrap();
            assert!(app.debug);
        });
    }

    #[tokio::test]
    async fn test_route_addition() {
        Python::with_gil(|py| {
            let app = RustletteApp::new(None, None, None).unwrap();

            let handler = py
                .eval("lambda request: 'Hello, World!'", None, None)
                .unwrap()
                .to_object(py);

            app.add_route(
                "/test".to_string(),
                handler,
                Some(vec!["GET".to_string()]),
                Some("test_route".to_string()),
                None,
            )
            .unwrap();
        });
    }

    #[test]
    fn test_asgi_creation() {
        Python::with_gil(|py| {
            let app = RustletteApp::new(None, None, None).unwrap();
            let asgi_app = app.asgi();

            // Test that we can create the ASGI app
            assert!(!format!("{:?}", asgi_app).is_empty());
        });
    }
}
