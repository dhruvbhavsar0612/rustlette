//! Rustlette - High-performance Python web framework with Rust internals
//!
//! This crate provides the Rust implementation of core web framework components
//! that are exposed to Python through PyO3 bindings.

use pyo3::prelude::*;

// Core modules
pub mod app;
pub mod asgi;
pub mod background;
pub mod error;
pub mod middleware;
pub mod request;
pub mod response;
pub mod routing;
pub mod server;
pub mod types;

// Re-export commonly used types
pub use app::RustletteApp;
pub use background::{BackgroundTask, BackgroundTaskManager};
pub use error::{RustletteError, RustletteResult};
pub use middleware::MiddlewareStack;
pub use request::RustletteRequest;
pub use response::{
    FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse,
    RustletteResponse, StreamingResponse,
};
pub use routing::{Route, RouteMatch, Router};
pub use server::RustletteServer;
pub use types::{HTTPMethod, Headers, QueryParams, StatusCode};

/// A minimal test function to verify PyO3 setup
#[pyfunction]
fn hello_rustlette() -> PyResult<String> {
    Ok("Hello from Rustlette!".to_string())
}

/// Python module definition
#[pymodule]
fn rustlette(_py: Python, m: &PyModule) -> PyResult<()> {
    // Add test function
    m.add_function(wrap_pyfunction!(hello_rustlette, m)?)?;

    // Add core types
    m.add_class::<types::HTTPMethod>()?;
    m.add_class::<types::StatusCode>()?;
    m.add_class::<types::Headers>()?;

    // Add request/response
    m.add_class::<request::RustletteRequest>()?;
    m.add_class::<response::RustletteResponse>()?;
    m.add_class::<response::JSONResponse>()?;
    m.add_class::<response::HTMLResponse>()?;
    m.add_class::<response::PlainTextResponse>()?;
    m.add_class::<response::RedirectResponse>()?;
    m.add_class::<response::FileResponse>()?;
    m.add_class::<response::StreamingResponse>()?;

    // Add routing
    m.add_class::<routing::Route>()?;
    m.add_class::<routing::Router>()?;

    // Add middleware
    m.add_class::<middleware::MiddlewareStack>()?;

    // Add background tasks
    m.add_class::<background::BackgroundTask>()?;
    m.add_class::<background::BackgroundTaskManager>()?;

    // Add application
    m.add_class::<app::RustletteApp>()?;

    // Add server
    m.add_class::<server::RustletteServer>()?;

    Ok(())
}
