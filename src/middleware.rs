//! Middleware system for Rustlette
//!
//! This module implements a middleware execution system that supports both
//! Python and Rust middleware with proper ordering and error handling.

use crate::error::{RustletteError, RustletteResult};
use crate::request::RustletteRequest;
use crate::response::RustletteResponse;
use async_trait::async_trait;
use pyo3::prelude::*;
use pyo3::types::PyType;
use std::collections::VecDeque;
use std::fmt;
use std::sync::Arc;

/// Trait for middleware that can process requests and responses
#[async_trait]
pub trait MiddlewareHandler: Send + Sync {
    /// Process a request before it reaches the handler
    async fn process_request(&self, request: &mut RustletteRequest) -> RustletteResult<()>;

    /// Process a response before it's sent to the client
    async fn process_response(
        &self,
        request: &RustletteRequest,
        response: &mut RustletteResponse,
    ) -> RustletteResult<()>;

    /// Called when an exception occurs in the request processing
    async fn process_exception(
        &self,
        request: &RustletteRequest,
        exception: &RustletteError,
    ) -> RustletteResult<Option<RustletteResponse>>;

    /// Get the middleware name for debugging
    fn name(&self) -> &str;
}

/// Python middleware wrapper
#[derive(Debug, Clone)]
pub struct PythonMiddleware {
    middleware: PyObject,
    name: String,
}

impl PythonMiddleware {
    pub fn new(middleware: PyObject, name: Option<String>) -> Self {
        let name = name.unwrap_or_else(|| {
            Python::with_gil(|py| {
                middleware
                    .getattr(py, "__class__")
                    .and_then(|cls| cls.getattr(py, "__name__"))
                    .and_then(|name| name.extract::<String>(py))
                    .unwrap_or_else(|_| "PythonMiddleware".to_string())
            })
        });

        Self { middleware, name }
    }
}

#[async_trait]
impl MiddlewareHandler for PythonMiddleware {
    async fn process_request(&self, request: &mut RustletteRequest) -> RustletteResult<()> {
        Python::with_gil(|py| {
            // Check if middleware has process_request method
            if self.middleware.as_ref(py).hasattr("process_request")? {
                let method = self.middleware.getattr(py, "process_request")?;
                let req_py = Py::new(py, request.clone())?;
                method.call1(py, (req_py,))?;
            }
            Ok(())
        })
        .map_err(|e: PyErr| {
            RustletteError::middleware_error(format!(
                "Error in {}.process_request: {}",
                self.name, e
            ))
        })
    }

    async fn process_response(
        &self,
        request: &RustletteRequest,
        response: &mut RustletteResponse,
    ) -> RustletteResult<()> {
        Python::with_gil(|py| {
            // Check if middleware has process_response method
            if self.middleware.as_ref(py).hasattr("process_response")? {
                let method = self.middleware.getattr(py, "process_response")?;
                let req_py = Py::new(py, request.clone())?;
                let resp_py = Py::new(py, response.clone())?;
                method.call1(py, (req_py, resp_py))?;
            }
            Ok(())
        })
        .map_err(|e: PyErr| {
            RustletteError::middleware_error(format!(
                "Error in {}.process_response: {}",
                self.name, e
            ))
        })
    }

    async fn process_exception(
        &self,
        request: &RustletteRequest,
        exception: &RustletteError,
    ) -> RustletteResult<Option<RustletteResponse>> {
        Python::with_gil(|py| {
            // Check if middleware has process_exception method
            if self.middleware.as_ref(py).hasattr("process_exception")? {
                let method = self.middleware.getattr(py, "process_exception")?;
                let req_py = Py::new(py, request.clone())?;
                let result = method.call1(py, (req_py, exception.clone()))?;

                if result.is_none(py) {
                    Ok(None)
                } else {
                    let response: RustletteResponse = result.extract(py)?;
                    Ok(Some(response))
                }
            } else {
                Ok(None)
            }
        })
        .map_err(|e: PyErr| {
            RustletteError::middleware_error(format!(
                "Error in {}.process_exception: {}",
                self.name, e
            ))
        })
    }

    fn name(&self) -> &str {
        &self.name
    }
}

/// Built-in CORS middleware
#[derive(Debug, Clone)]
pub struct CORSMiddleware {
    allow_origins: Vec<String>,
    allow_methods: Vec<String>,
    allow_headers: Vec<String>,
    allow_credentials: bool,
    expose_headers: Vec<String>,
    max_age: Option<u32>,
}

impl CORSMiddleware {
    pub fn new(
        allow_origins: Vec<String>,
        allow_methods: Vec<String>,
        allow_headers: Vec<String>,
        allow_credentials: bool,
        expose_headers: Vec<String>,
        max_age: Option<u32>,
    ) -> Self {
        Self {
            allow_origins,
            allow_methods,
            allow_headers,
            allow_credentials,
            expose_headers,
            max_age,
        }
    }

    pub fn permissive() -> Self {
        Self {
            allow_origins: vec!["*".to_string()],
            allow_methods: vec![
                "GET".to_string(),
                "POST".to_string(),
                "PUT".to_string(),
                "DELETE".to_string(),
                "OPTIONS".to_string(),
                "HEAD".to_string(),
                "PATCH".to_string(),
            ],
            allow_headers: vec!["*".to_string()],
            allow_credentials: false,
            expose_headers: vec![],
            max_age: Some(86400), // 24 hours
        }
    }

    fn is_origin_allowed(&self, origin: &str) -> bool {
        self.allow_origins.contains(&"*".to_string())
            || self.allow_origins.contains(&origin.to_string())
    }
}

#[async_trait]
impl MiddlewareHandler for CORSMiddleware {
    async fn process_request(&self, _request: &mut RustletteRequest) -> RustletteResult<()> {
        // CORS processing is mainly done in process_response
        Ok(())
    }

    async fn process_response(
        &self,
        request: &RustletteRequest,
        response: &mut RustletteResponse,
    ) -> RustletteResult<()> {
        // Add CORS headers
        let origin = request.headers.get("origin");

        if let Some(origin) = origin {
            if self.is_origin_allowed(&origin) {
                response.headers.set("access-control-allow-origin", &origin);
            }
        } else if self.allow_origins.contains(&"*".to_string()) {
            response.headers.set("access-control-allow-origin", "*");
        }

        if !self.allow_methods.is_empty() {
            response.headers.set(
                "access-control-allow-methods",
                &self.allow_methods.join(", "),
            );
        }

        if !self.allow_headers.is_empty() {
            response.headers.set(
                "access-control-allow-headers",
                &self.allow_headers.join(", "),
            );
        }

        if self.allow_credentials {
            response
                .headers
                .set("access-control-allow-credentials", "true");
        }

        if !self.expose_headers.is_empty() {
            response.headers.set(
                "access-control-expose-headers",
                &self.expose_headers.join(", "),
            );
        }

        if let Some(max_age) = self.max_age {
            response
                .headers
                .set("access-control-max-age", &max_age.to_string());
        }

        Ok(())
    }

    async fn process_exception(
        &self,
        _request: &RustletteRequest,
        _exception: &RustletteError,
    ) -> RustletteResult<Option<RustletteResponse>> {
        Ok(None)
    }

    fn name(&self) -> &str {
        "CORSMiddleware"
    }
}

/// Security headers middleware
#[derive(Debug, Clone)]
pub struct SecurityHeadersMiddleware {
    content_type_nosniff: bool,
    frame_options: Option<String>,
    xss_protection: bool,
    hsts_max_age: Option<u32>,
    hsts_include_subdomains: bool,
    referrer_policy: Option<String>,
    content_security_policy: Option<String>,
}

impl SecurityHeadersMiddleware {
    pub fn new() -> Self {
        Self {
            content_type_nosniff: true,
            frame_options: Some("DENY".to_string()),
            xss_protection: true,
            hsts_max_age: Some(31536000), // 1 year
            hsts_include_subdomains: true,
            referrer_policy: Some("strict-origin-when-cross-origin".to_string()),
            content_security_policy: None,
        }
    }

    pub fn with_csp(mut self, csp: String) -> Self {
        self.content_security_policy = Some(csp);
        self
    }

    pub fn with_frame_options(mut self, frame_options: String) -> Self {
        self.frame_options = Some(frame_options);
        self
    }
}

impl Default for SecurityHeadersMiddleware {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl MiddlewareHandler for SecurityHeadersMiddleware {
    async fn process_request(&self, _request: &mut RustletteRequest) -> RustletteResult<()> {
        Ok(())
    }

    async fn process_response(
        &self,
        request: &RustletteRequest,
        response: &mut RustletteResponse,
    ) -> RustletteResult<()> {
        if self.content_type_nosniff {
            response.headers.set("x-content-type-options", "nosniff");
        }

        if let Some(ref frame_options) = self.frame_options {
            response.headers.set("x-frame-options", frame_options);
        }

        if self.xss_protection {
            response.headers.set("x-xss-protection", "1; mode=block");
        }

        // Only set HSTS for HTTPS requests
        let is_https = request.url.starts_with("https://");
        if is_https {
            if let Some(max_age) = self.hsts_max_age {
                let hsts_value = if self.hsts_include_subdomains {
                    format!("max-age={}; includeSubDomains", max_age)
                } else {
                    format!("max-age={}", max_age)
                };
                response
                    .headers
                    .set("strict-transport-security", &hsts_value);
            }
        }

        if let Some(ref referrer_policy) = self.referrer_policy {
            response.headers.set("referrer-policy", referrer_policy);
        }

        if let Some(ref csp) = self.content_security_policy {
            response.headers.set("content-security-policy", csp);
        }

        Ok(())
    }

    async fn process_exception(
        &self,
        _request: &RustletteRequest,
        _exception: &RustletteError,
    ) -> RustletteResult<Option<RustletteResponse>> {
        Ok(None)
    }

    fn name(&self) -> &str {
        "SecurityHeadersMiddleware"
    }
}

/// Request timing middleware
#[derive(Debug, Clone)]
pub struct TimingMiddleware {
    header_name: String,
}

impl TimingMiddleware {
    pub fn new(header_name: Option<String>) -> Self {
        Self {
            header_name: header_name.unwrap_or_else(|| "X-Process-Time".to_string()),
        }
    }
}

impl Default for TimingMiddleware {
    fn default() -> Self {
        Self::new(None)
    }
}

#[async_trait]
impl MiddlewareHandler for TimingMiddleware {
    async fn process_request(&self, request: &mut RustletteRequest) -> RustletteResult<()> {
        let start_time = std::time::Instant::now();
        request.state_set(
            "request_start_time".to_string(),
            Python::with_gil(|py| start_time.elapsed().as_secs_f64().to_object(py)),
        );
        Ok(())
    }

    async fn process_response(
        &self,
        request: &RustletteRequest,
        response: &mut RustletteResponse,
    ) -> RustletteResult<()> {
        if let Some(start_time_obj) = request.state_get("request_start_time") {
            Python::with_gil(|py| {
                if let Ok(start_time) = start_time_obj.extract::<f64>(py) {
                    let duration = std::time::Instant::now().elapsed().as_secs_f64() - start_time;
                    response
                        .headers
                        .set(&self.header_name, &format!("{:.6}", duration));
                }
            });
        }
        Ok(())
    }

    async fn process_exception(
        &self,
        _request: &RustletteRequest,
        _exception: &RustletteError,
    ) -> RustletteResult<Option<RustletteResponse>> {
        Ok(None)
    }

    fn name(&self) -> &str {
        "TimingMiddleware"
    }
}

/// Middleware wrapper for the Python interface
#[derive(Clone)]
#[pyclass]
pub struct Middleware {
    handler: Arc<dyn MiddlewareHandler>,
}

#[pymethods]
impl Middleware {
    #[new]
    pub fn new(middleware: PyObject, name: Option<String>) -> Self {
        Self {
            handler: Arc::new(PythonMiddleware::new(middleware, name)),
        }
    }

    /// Create CORS middleware
    #[classmethod]
    fn cors(
        _cls: &PyType,
        allow_origins: Option<Vec<String>>,
        allow_methods: Option<Vec<String>>,
        allow_headers: Option<Vec<String>>,
        allow_credentials: Option<bool>,
        expose_headers: Option<Vec<String>>,
        max_age: Option<u32>,
    ) -> Self {
        let cors = CORSMiddleware::new(
            allow_origins.unwrap_or_else(|| vec!["*".to_string()]),
            allow_methods.unwrap_or_else(|| {
                vec![
                    "GET".to_string(),
                    "POST".to_string(),
                    "PUT".to_string(),
                    "DELETE".to_string(),
                    "OPTIONS".to_string(),
                ]
            }),
            allow_headers.unwrap_or_else(|| vec!["*".to_string()]),
            allow_credentials.unwrap_or(false),
            expose_headers.unwrap_or_default(),
            max_age,
        );

        Self {
            handler: Arc::new(cors),
        }
    }

    /// Create security headers middleware
    #[classmethod]
    fn security_headers(_cls: &PyType) -> Self {
        Self {
            handler: Arc::new(SecurityHeadersMiddleware::new()),
        }
    }

    /// Create timing middleware
    #[classmethod]
    fn timing(_cls: &PyType, header_name: Option<String>) -> Self {
        Self {
            handler: Arc::new(TimingMiddleware::new(header_name)),
        }
    }

    #[getter]
    fn name(&self) -> String {
        self.handler.name().to_string()
    }

    fn __repr__(&self) -> String {
        format!("Middleware({})", self.handler.name())
    }
}

impl Middleware {
    pub fn handler(&self) -> Arc<dyn MiddlewareHandler> {
        self.handler.clone()
    }
}

/// Middleware execution stack
#[pyclass]
pub struct MiddlewareStack {
    middlewares: Vec<Arc<dyn MiddlewareHandler>>,
}

#[pymethods]
impl MiddlewareStack {
    #[new]
    pub fn new() -> Self {
        Self {
            middlewares: Vec::new(),
        }
    }

    /// Add middleware to the stack
    pub fn add(&mut self, middleware: Middleware) {
        self.middlewares.push(middleware.handler());
    }

    /// Insert middleware at a specific position
    pub fn insert(&mut self, index: usize, middleware: Middleware) -> PyResult<()> {
        if index > self.middlewares.len() {
            return Err(pyo3::exceptions::PyIndexError::new_err(
                "Middleware index out of range",
            ));
        }
        self.middlewares.insert(index, middleware.handler());
        Ok(())
    }

    /// Remove middleware at a specific position
    pub fn remove(&mut self, index: usize) -> PyResult<()> {
        if index >= self.middlewares.len() {
            return Err(pyo3::exceptions::PyIndexError::new_err(
                "Middleware index out of range",
            ));
        }
        self.middlewares.remove(index);
        Ok(())
    }

    /// Get the number of middlewares
    pub fn len(&self) -> usize {
        self.middlewares.len()
    }

    /// Check if the stack is empty
    pub fn is_empty(&self) -> bool {
        self.middlewares.is_empty()
    }

    /// Clear all middlewares
    pub fn clear(&mut self) {
        self.middlewares.clear();
    }

    fn __len__(&self) -> usize {
        self.len()
    }

    fn __repr__(&self) -> String {
        format!("MiddlewareStack({} middlewares)", self.middlewares.len())
    }
}

impl Default for MiddlewareStack {
    fn default() -> Self {
        Self::new()
    }
}

impl MiddlewareStack {
    /// Process request through all middlewares
    pub async fn process_request(&self, request: &mut RustletteRequest) -> RustletteResult<()> {
        for middleware in &self.middlewares {
            middleware.process_request(request).await.map_err(|e| {
                tracing::error!("Error in middleware {}: {}", middleware.name(), e);
                e
            })?;
        }
        Ok(())
    }

    /// Process response through all middlewares (in reverse order)
    pub async fn process_response(
        &self,
        request: &RustletteRequest,
        response: &mut RustletteResponse,
    ) -> RustletteResult<()> {
        for middleware in self.middlewares.iter().rev() {
            middleware
                .process_response(request, response)
                .await
                .map_err(|e| {
                    tracing::error!("Error in middleware {}: {}", middleware.name(), e);
                    e
                })?;
        }
        Ok(())
    }

    /// Process exception through all middlewares
    pub async fn process_exception(
        &self,
        request: &RustletteRequest,
        exception: &RustletteError,
    ) -> RustletteResult<Option<RustletteResponse>> {
        for middleware in &self.middlewares {
            if let Some(response) = middleware
                .process_exception(request, exception)
                .await
                .map_err(|e| {
                    tracing::error!("Error in middleware {}: {}", middleware.name(), e);
                    e
                })?
            {
                return Ok(Some(response));
            }
        }
        Ok(None)
    }

    /// Add a Python middleware
    pub fn add_python_middleware(&mut self, middleware: PyObject, name: Option<String>) {
        self.middlewares
            .push(Arc::new(PythonMiddleware::new(middleware, name)));
    }

    /// Add built-in CORS middleware
    pub fn add_cors_middleware(
        &mut self,
        allow_origins: Option<Vec<String>>,
        allow_methods: Option<Vec<String>>,
        allow_headers: Option<Vec<String>>,
        allow_credentials: Option<bool>,
        expose_headers: Option<Vec<String>>,
        max_age: Option<u32>,
    ) {
        let cors = CORSMiddleware::new(
            allow_origins.unwrap_or_else(|| vec!["*".to_string()]),
            allow_methods.unwrap_or_else(|| {
                vec![
                    "GET".to_string(),
                    "POST".to_string(),
                    "PUT".to_string(),
                    "DELETE".to_string(),
                    "OPTIONS".to_string(),
                ]
            }),
            allow_headers.unwrap_or_else(|| vec!["*".to_string()]),
            allow_credentials.unwrap_or(false),
            expose_headers.unwrap_or_default(),
            max_age,
        );
        self.middlewares.push(Arc::new(cors));
    }

    /// Add security headers middleware
    pub fn add_security_headers_middleware(&mut self) {
        self.middlewares
            .push(Arc::new(SecurityHeadersMiddleware::new()));
    }

    /// Add timing middleware
    pub fn add_timing_middleware(&mut self, header_name: Option<String>) {
        self.middlewares
            .push(Arc::new(TimingMiddleware::new(header_name)));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::HTTPMethod;

    #[tokio::test]
    async fn test_cors_middleware() {
        let cors = CORSMiddleware::permissive();

        let mut request = RustletteRequest::new(
            "GET".to_string(),
            "https://example.com/api".to_string(),
            None,
            None,
            None,
        )
        .unwrap();

        request.headers.set("origin", "https://frontend.com");

        let mut response = RustletteResponse::new(
            Some(Python::with_gil(|py| "OK".to_object(py))),
            Some(200),
            None,
            None,
            None,
        )
        .unwrap();

        cors.process_response(&request, &mut response)
            .await
            .unwrap();

        assert_eq!(
            response.headers.get("access-control-allow-origin"),
            Some("https://frontend.com".to_string())
        );
    }

    #[tokio::test]
    async fn test_security_headers_middleware() {
        let security = SecurityHeadersMiddleware::new();

        let request = RustletteRequest::new(
            "GET".to_string(),
            "https://example.com/api".to_string(),
            None,
            None,
            None,
        )
        .unwrap();

        let mut response = RustletteResponse::new(
            Some(Python::with_gil(|py| "OK".to_object(py))),
            Some(200),
            None,
            None,
            None,
        )
        .unwrap();

        security
            .process_response(&request, &mut response)
            .await
            .unwrap();

        assert_eq!(
            response.headers.get("x-content-type-options"),
            Some("nosniff".to_string())
        );
        assert_eq!(
            response.headers.get("x-frame-options"),
            Some("DENY".to_string())
        );
    }

    #[tokio::test]
    async fn test_middleware_stack() {
        let mut stack = MiddlewareStack::new();

        stack.add_cors_middleware(None, None, None, None, None, None);
        stack.add_security_headers_middleware();

        assert_eq!(stack.len(), 2);

        let mut request = RustletteRequest::new(
            "GET".to_string(),
            "https://example.com/api".to_string(),
            None,
            None,
            None,
        )
        .unwrap();

        // Test request processing
        stack.process_request(&mut request).await.unwrap();

        // Test response processing
        let mut response = RustletteResponse::new(
            Some(Python::with_gil(|py| "OK".to_object(py))),
            Some(200),
            None,
            None,
            None,
        )
        .unwrap();

        stack
            .process_response(&request, &mut response)
            .await
            .unwrap();

        // Both CORS and security headers should be present
        assert!(response.headers.contains("access-control-allow-origin"));
        assert!(response.headers.contains("x-content-type-options"));
    }
}
