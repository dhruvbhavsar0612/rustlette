//! HTTP server implementation for Rustlette
//!
//! This module implements a high-performance HTTP server using Tokio and Hyper
//! that serves as the runtime for Rustlette applications.

use crate::app::RustletteApp;
use crate::error::{RustletteError, RustletteResult};
use crate::request::RustletteRequest;
use crate::response::RustletteResponse;
use crate::types::{HTTPMethod, Headers};
use bytes::Bytes;
use futures::future::BoxFuture;
use hyper::service::{make_service_fn, service_fn};
use hyper::{Body, Method, Request, Response, Server, StatusCode};
use pyo3::prelude::*;
use std::convert::Infallible;
use std::net::SocketAddr;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::signal;
use tokio::sync::RwLock;
use tracing::{error, info, warn};

/// Server configuration
#[derive(Debug, Clone)]
pub struct ServerConfig {
    pub host: String,
    pub port: u16,
    pub workers: Option<usize>,
    pub max_connections: Option<usize>,
    pub keep_alive_timeout: Option<Duration>,
    pub read_timeout: Option<Duration>,
    pub write_timeout: Option<Duration>,
    pub max_request_size: Option<usize>,
    pub enable_access_log: bool,
    pub enable_gzip: bool,
    pub ssl_cert_path: Option<String>,
    pub ssl_key_path: Option<String>,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            host: "127.0.0.1".to_string(),
            port: 8000,
            workers: None,
            max_connections: Some(1000),
            keep_alive_timeout: Some(Duration::from_secs(5)),
            read_timeout: Some(Duration::from_secs(30)),
            write_timeout: Some(Duration::from_secs(30)),
            max_request_size: Some(16 * 1024 * 1024), // 16MB
            enable_access_log: true,
            enable_gzip: false,
            ssl_cert_path: None,
            ssl_key_path: None,
        }
    }
}

/// HTTP server for Rustlette applications
#[derive(Debug)]
#[pyclass]
pub struct RustletteServer {
    app: Arc<RustletteApp>,
    config: ServerConfig,
    shutdown_signal: Arc<RwLock<Option<tokio::sync::oneshot::Sender<()>>>>,
}

#[pymethods]
impl RustletteServer {
    #[new]
    #[pyo3(signature = (app, host=None, port=None, **kwargs))]
    pub fn new(
        app: RustletteApp,
        host: Option<String>,
        port: Option<u16>,
        kwargs: Option<&pyo3::types::PyDict>,
    ) -> PyResult<Self> {
        let mut config = ServerConfig::default();

        if let Some(host) = host {
            config.host = host;
        }

        if let Some(port) = port {
            config.port = port;
        }

        // Parse additional configuration from kwargs
        if let Some(kwargs) = kwargs {
            if let Some(workers) = kwargs.get_item("workers") {
                config.workers = workers.extract()?;
            }
            if let Some(max_connections) = kwargs.get_item("max_connections") {
                config.max_connections = max_connections.extract()?;
            }
            if let Some(keep_alive) = kwargs.get_item("keep_alive_timeout") {
                let secs: f64 = keep_alive.extract()?;
                config.keep_alive_timeout = Some(Duration::from_secs_f64(secs));
            }
            if let Some(read_timeout) = kwargs.get_item("read_timeout") {
                let secs: f64 = read_timeout.extract()?;
                config.read_timeout = Some(Duration::from_secs_f64(secs));
            }
            if let Some(write_timeout) = kwargs.get_item("write_timeout") {
                let secs: f64 = write_timeout.extract()?;
                config.write_timeout = Some(Duration::from_secs_f64(secs));
            }
            if let Some(max_size) = kwargs.get_item("max_request_size") {
                config.max_request_size = max_size.extract()?;
            }
            if let Some(access_log) = kwargs.get_item("access_log") {
                config.enable_access_log = access_log.extract()?;
            }
            if let Some(gzip) = kwargs.get_item("gzip") {
                config.enable_gzip = gzip.extract()?;
            }
            if let Some(ssl_cert) = kwargs.get_item("ssl_cert") {
                config.ssl_cert_path = ssl_cert.extract()?;
            }
            if let Some(ssl_key) = kwargs.get_item("ssl_key") {
                config.ssl_key_path = ssl_key.extract()?;
            }
        }

        Ok(Self {
            app: Arc::new(app),
            config,
            shutdown_signal: Arc::new(RwLock::new(None)),
        })
    }

    /// Start the server
    pub fn serve(&self) -> PyResult<()> {
        Python::with_gil(|py| {
            let server = self.clone();
            pyo3_asyncio::tokio::future_into_py(py, async move { server.run().await })
        })
    }

    /// Start the server with automatic reload (development mode)
    pub fn serve_with_reload(&self, reload_dirs: Option<Vec<String>>) -> PyResult<()> {
        Python::with_gil(|py| {
            let server = self.clone();
            pyo3_asyncio::tokio::future_into_py(py, async move {
                // For now, just run normally
                // In a full implementation, this would watch files and reload
                warn!("Auto-reload not yet implemented, running normally");
                server.run().await
            })
        })
    }

    /// Stop the server gracefully
    pub fn shutdown(&self) -> PyResult<()> {
        Python::with_gil(|py| {
            let shutdown_signal = self.shutdown_signal.clone();
            pyo3_asyncio::tokio::future_into_py(py, async move {
                let mut signal = shutdown_signal.write().await;
                if let Some(sender) = signal.take() {
                    let _ = sender.send(());
                    info!("Server shutdown signal sent");
                }
                Ok(())
            })
        })
    }

    /// Get server configuration
    #[getter]
    pub fn config(&self) -> PyResult<pyo3::PyObject> {
        Python::with_gil(|py| {
            let dict = pyo3::types::PyDict::new(py);
            dict.set_item("host", &self.config.host)?;
            dict.set_item("port", self.config.port)?;
            dict.set_item("workers", self.config.workers)?;
            dict.set_item("max_connections", self.config.max_connections)?;
            dict.set_item("enable_access_log", self.config.enable_access_log)?;
            dict.set_item("enable_gzip", self.config.enable_gzip)?;
            Ok(dict.into())
        })
    }

    /// Get server address
    #[getter]
    pub fn address(&self) -> String {
        format!("{}:{}", self.config.host, self.config.port)
    }

    fn __repr__(&self) -> String {
        format!(
            "RustletteServer(host='{}', port={})",
            self.config.host, self.config.port
        )
    }
}

impl Clone for RustletteServer {
    fn clone(&self) -> Self {
        Self {
            app: Arc::clone(&self.app),
            config: self.config.clone(),
            shutdown_signal: Arc::clone(&self.shutdown_signal),
        }
    }
}

impl RustletteServer {
    /// Run the server
    pub async fn run(&self) -> PyResult<()> {
        // Run startup handlers
        self.app.startup().await.map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!("Startup failed: {}", e))
        })?;

        let addr: SocketAddr = format!("{}:{}", self.config.host, self.config.port)
            .parse()
            .map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(format!("Invalid address: {}", e))
            })?;

        info!("Starting Rustlette server on {}", addr);

        // Create service
        let app = Arc::clone(&self.app);
        let config = self.config.clone();
        let make_svc = make_service_fn(move |_conn| {
            let app = Arc::clone(&app);
            let config = config.clone();
            async move {
                Ok::<_, Infallible>(service_fn(move |req| {
                    handle_request(Arc::clone(&app), config.clone(), req)
                }))
            }
        });

        // Create server
        let server = Server::bind(&addr).serve(make_svc);

        // Set up graceful shutdown
        let (shutdown_tx, shutdown_rx) = tokio::sync::oneshot::channel();
        {
            let mut signal = self.shutdown_signal.write().await;
            *signal = Some(shutdown_tx);
        }

        let graceful = server.with_graceful_shutdown(async {
            // Wait for shutdown signal or SIGINT/SIGTERM
            tokio::select! {
                _ = shutdown_rx => {
                    info!("Received graceful shutdown signal");
                }
                _ = signal::ctrl_c() => {
                    info!("Received SIGINT, shutting down gracefully");
                }
                _ = async {
                    #[cfg(unix)]
                    {
                        let mut sigterm = signal::unix::signal(signal::unix::SignalKind::terminate()).unwrap();
                        sigterm.recv().await;
                    }
                    #[cfg(not(unix))]
                    {
                        std::future::pending::<()>().await;
                    }
                } => {
                    info!("Received SIGTERM, shutting down gracefully");
                }
            }
        });

        info!("Server running on http://{}", addr);

        // Run the server
        if let Err(e) = graceful.await {
            error!("Server error: {}", e);
            return Err(pyo3::exceptions::PyRuntimeError::new_err(format!(
                "Server error: {}",
                e
            )));
        }

        // Run shutdown handlers
        self.app.shutdown().await.map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!("Shutdown failed: {}", e))
        })?;

        info!("Server stopped");
        Ok(())
    }
}

/// Handle a single HTTP request
async fn handle_request(
    app: Arc<RustletteApp>,
    config: ServerConfig,
    req: Request<Body>,
) -> Result<Response<Body>, Infallible> {
    let start_time = Instant::now();
    let method = req.method().clone();
    let uri = req.uri().clone();

    let result = process_request(app, config.clone(), req).await;

    match result {
        Ok(response) => {
            let duration = start_time.elapsed();
            let status = response.status();

            if config.enable_access_log {
                info!(
                    "{} {} {} - {:?}",
                    method,
                    uri.path(),
                    status.as_u16(),
                    duration
                );
            }

            Ok(response)
        }
        Err(e) => {
            let duration = start_time.elapsed();
            error!("Request processing failed: {} - {:?}", e, duration);

            let response = Response::builder()
                .status(StatusCode::INTERNAL_SERVER_ERROR)
                .header("content-type", "text/plain")
                .body(Body::from("Internal Server Error"))
                .unwrap_or_else(|_| Response::default());

            Ok(response)
        }
    }
}

/// Process an HTTP request through the application
async fn process_request(
    app: Arc<RustletteApp>,
    config: ServerConfig,
    req: Request<Body>,
) -> RustletteResult<Response<Body>> {
    let (parts, body) = req.into_parts();

    // Check request size limit
    if let Some(max_size) = config.max_request_size {
        if let Some(content_length) = parts.headers.get("content-length") {
            if let Ok(length_str) = content_length.to_str() {
                if let Ok(length) = length_str.parse::<usize>() {
                    if length > max_size {
                        return Ok(Response::builder()
                            .status(StatusCode::PAYLOAD_TOO_LARGE)
                            .header("content-type", "text/plain")
                            .body(Body::from("Request too large"))?);
                    }
                }
            }
        }
    }

    // Read request body
    let body_bytes = match hyper::body::to_bytes(body).await {
        Ok(bytes) => Some(bytes),
        Err(e) => {
            warn!("Failed to read request body: {}", e);
            None
        }
    };

    // Convert to Rustlette request
    let rustlette_request =
        RustletteRequest::from_hyper_request(parts.method, parts.uri, parts.headers, body_bytes)?;

    // Process through the app
    let rustlette_response = app
        .process_request(rustlette_request)
        .await
        .map_err(|e| RustletteError::internal_error(e.to_string()))?;

    // Convert to Hyper response
    let response = convert_response(rustlette_response, &config)?;

    Ok(response)
}

/// Convert a Rustlette response to a Hyper response
fn convert_response(
    rustlette_response: RustletteResponse,
    config: &ServerConfig,
) -> RustletteResult<Response<Body>> {
    let mut builder = Response::builder().status(rustlette_response.status_code);

    // Add headers
    for key in rustlette_response.headers.keys() {
        if let Some(value) = rustlette_response.headers.get(&key) {
            builder = builder.header(&key, &value);
        }
    }

    // Add default headers
    builder = builder.header("server", "Rustlette/0.1.0");

    // Get body
    let body = if let Some(body_bytes) = rustlette_response.raw_body() {
        let mut body_data = body_bytes.clone();

        // Apply gzip compression if enabled and client accepts it
        if config.enable_gzip {
            // TODO: Check Accept-Encoding header and compress if needed
            // For now, we'll skip compression
        }

        Body::from(body_data)
    } else {
        Body::empty()
    };

    let response = builder.body(body)?;
    Ok(response)
}

/// Development server utilities
pub mod dev {
    use super::*;
    use std::path::Path;

    /// Start a development server with hot reload
    pub async fn run_dev_server(
        app: Arc<RustletteApp>,
        host: &str,
        port: u16,
        reload_dirs: Vec<String>,
    ) -> RustletteResult<()> {
        let config = ServerConfig {
            host: host.to_string(),
            port,
            enable_access_log: true,
            ..Default::default()
        };

        let server = RustletteServer {
            app,
            config,
            shutdown_signal: Arc::new(RwLock::new(None)),
        };

        // TODO: Implement file watching for hot reload
        info!("Development server starting (hot reload not yet implemented)");
        server.run().await?;

        Ok(())
    }

    /// Watch files for changes
    pub async fn watch_files(
        _paths: Vec<String>,
        _callback: impl Fn() + Send + 'static,
    ) -> RustletteResult<()> {
        // TODO: Implement file watching using notify crate
        warn!("File watching not yet implemented");
        Ok(())
    }
}

/// Production server utilities
pub mod prod {
    use super::*;

    /// Production server configuration
    pub struct ProdConfig {
        pub workers: usize,
        pub max_connections: usize,
        pub enable_ssl: bool,
        pub ssl_cert_path: Option<String>,
        pub ssl_key_path: Option<String>,
        pub enable_http2: bool,
        pub enable_compression: bool,
    }

    impl Default for ProdConfig {
        fn default() -> Self {
            Self {
                workers: num_cpus::get(),
                max_connections: 10000,
                enable_ssl: false,
                ssl_cert_path: None,
                ssl_key_path: None,
                enable_http2: false,
                enable_compression: true,
            }
        }
    }

    /// Start a production server
    pub async fn run_prod_server(
        app: Arc<RustletteApp>,
        host: &str,
        port: u16,
        prod_config: ProdConfig,
    ) -> RustletteResult<()> {
        let config = ServerConfig {
            host: host.to_string(),
            port,
            workers: Some(prod_config.workers),
            max_connections: Some(prod_config.max_connections),
            enable_gzip: prod_config.enable_compression,
            ssl_cert_path: prod_config.ssl_cert_path,
            ssl_key_path: prod_config.ssl_key_path,
            ..Default::default()
        };

        let server = RustletteServer {
            app,
            config,
            shutdown_signal: Arc::new(RwLock::new(None)),
        };

        info!(
            "Production server starting with {} workers",
            prod_config.workers
        );
        server.run().await?;

        Ok(())
    }
}

/// Helper functions for server management
pub mod helpers {
    use super::*;

    /// Create a simple server for testing
    pub fn create_test_server(app: RustletteApp) -> RustletteServer {
        RustletteServer {
            app: Arc::new(app),
            config: ServerConfig {
                host: "127.0.0.1".to_string(),
                port: 0, // Random port
                enable_access_log: false,
                ..Default::default()
            },
            shutdown_signal: Arc::new(RwLock::new(None)),
        }
    }

    /// Get an available port
    pub fn get_available_port() -> RustletteResult<u16> {
        use std::net::TcpListener;

        let listener = TcpListener::bind("127.0.0.1:0")
            .map_err(|e| RustletteError::server_error(format!("Failed to bind to port: {}", e)))?;

        let port = listener
            .local_addr()
            .map_err(|e| {
                RustletteError::server_error(format!("Failed to get local address: {}", e))
            })?
            .port();

        Ok(port)
    }

    /// Validate server configuration
    pub fn validate_config(config: &ServerConfig) -> RustletteResult<()> {
        if config.port == 0 {
            return Err(RustletteError::server_error("Port cannot be 0"));
        }

        if config.host.is_empty() {
            return Err(RustletteError::server_error("Host cannot be empty"));
        }

        if let Some(max_size) = config.max_request_size {
            if max_size == 0 {
                return Err(RustletteError::server_error("Max request size cannot be 0"));
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::app::RustletteApp;

    #[test]
    fn test_server_config() {
        let config = ServerConfig::default();
        assert_eq!(config.host, "127.0.0.1");
        assert_eq!(config.port, 8000);
        assert!(config.enable_access_log);
    }

    #[test]
    fn test_server_creation() {
        Python::with_gil(|py| {
            let app = RustletteApp::new(None, None, None).unwrap();
            let server = RustletteServer::new(app, None, None, None).unwrap();
            assert_eq!(server.config.host, "127.0.0.1");
            assert_eq!(server.config.port, 8000);
        });
    }

    #[test]
    fn test_available_port() {
        let port = helpers::get_available_port().unwrap();
        assert!(port > 0);
    }

    #[test]
    fn test_config_validation() {
        let config = ServerConfig::default();
        assert!(helpers::validate_config(&config).is_ok());

        let invalid_config = ServerConfig {
            port: 0,
            ..Default::default()
        };
        assert!(helpers::validate_config(&invalid_config).is_err());
    }

    #[tokio::test]
    async fn test_response_conversion() {
        Python::with_gil(|py| {
            let response = RustletteResponse::new(
                Some("Hello, World!".to_object(py)),
                Some(200),
                None,
                None,
                None,
            )
            .unwrap();

            let config = ServerConfig::default();
            let hyper_response = convert_response(response, &config).unwrap();

            assert_eq!(hyper_response.status(), StatusCode::OK);
        });
    }
}
