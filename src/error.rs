//! Error handling for Rustlette
//!
//! This module defines the error types used throughout the Rustlette framework
//! and provides conversions to Python exceptions.

use pyo3::prelude::*;
use pyo3::exceptions::{PyException, PyRuntimeError, PyValueError};
use std::fmt;

/// Result type alias for Rustlette operations
pub type RustletteResult<T> = Result<T, RustletteError>;

/// Main error type for Rustlette operations
#[derive(Debug, Clone)]
#[pyclass(extends=PyException)]
pub struct RustletteError {
    #[pyo3(get)]
    pub message: String,
    #[pyo3(get)]
    pub error_type: String,
    #[pyo3(get)]
    pub status_code: Option<u16>,
}

#[pymethods]
impl RustletteError {
    #[new]
    pub fn new(message: String, error_type: Option<String>, status_code: Option<u16>) -> Self {
        Self {
            message,
            error_type: error_type.unwrap_or_else(|| "RustletteError".to_string()),
            status_code,
        }
    }

    fn __str__(&self) -> String {
        format!("{}: {}", self.error_type, self.message)
    }

    fn __repr__(&self) -> String {
        format!(
            "RustletteError(message='{}', error_type='{}', status_code={:?})",
            self.message, self.error_type, self.status_code
        )
    }
}

impl fmt::Display for RustletteError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.error_type, self.message)
    }
}

impl std::error::Error for RustletteError {}

impl From<RustletteError> for PyErr {
    fn from(err: RustletteError) -> PyErr {
        PyRuntimeError::new_err(err.message)
    }
}

/// Specific error types for different operations
impl RustletteError {
    /// Create a routing error
    pub fn routing_error(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
            error_type: "RoutingError".to_string(),
            status_code: Some(404),
        }
    }

    /// Create a middleware error
    pub fn middleware_error(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
            error_type: "MiddlewareError".to_string(),
            status_code: Some(500),
        }
    }

    /// Create a request parsing error
    pub fn request_error(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
            error_type: "RequestError".to_string(),
            status_code: Some(400),
        }
    }

    /// Create a response error
    pub fn response_error(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
            error_type: "ResponseError".to_string(),
            status_code: Some(500),
        }
    }

    /// Create a server error
    pub fn server_error(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
            error_type: "ServerError".to_string(),
            status_code: Some(500),
        }
    }

    /// Create a validation error
    pub fn validation_error(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
            error_type: "ValidationError".to_string(),
            status_code: Some(422),
        }
    }

    /// Create an authentication error
    pub fn auth_error(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
            error_type: "AuthenticationError".to_string(),
            status_code: Some(401),
        }
    }

    /// Create an authorization error
    pub fn authz_error(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
            error_type: "AuthorizationError".to_string(),
            status_code: Some(403),
        }
    }

    /// Create a timeout error
    pub fn timeout_error(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
            error_type: "TimeoutError".to_string(),
            status_code: Some(408),
        }
    }

    /// Create a not found error
    pub fn not_found(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
            error_type: "NotFound".to_string(),
            status_code: Some(404),
        }
    }

    /// Create a method not allowed error
    pub fn method_not_allowed(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
            error_type: "MethodNotAllowed".to_string(),
            status_code: Some(405),
        }
    }

    /// Create an internal server error
    pub fn internal_error(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
            error_type: "InternalServerError".to_string(),
            status_code: Some(500),
        }
    }
}

/// Convert various external errors to RustletteError
impl From<hyper::Error> for RustletteError {
    fn from(err: hyper::Error) -> Self {
        RustletteError::server_error(format!("HTTP server error: {}", err))
    }
}

impl From<std::io::Error> for RustletteError {
    fn from(err: std::io::Error) -> Self {
        RustletteError::server_error(format!("IO error: {}", err))
    }
}

impl From<serde_json::Error> for RustletteError {
    fn from(err: serde_json::Error) -> Self {
        RustletteError::request_error(format!("JSON parsing error: {}", err))
    }
}

impl From<url::ParseError> for RustletteError {
    fn from(err: url::ParseError) -> Self {
        RustletteError::request_error(format!("URL parsing error: {}", err))
    }
}

impl From<regex::Error> for RustletteError {
    fn from(err: regex::Error) -> Self {
        RustletteError::routing_error(format!("Regex error: {}", err))
    }
}

impl From<http::Error> for RustletteError {
    fn from(err: http::Error) -> Self {
        RustletteError::request_error(format!("HTTP error: {}", err))
    }
}

impl From<http::header::InvalidHeaderValue> for RustletteError {
    fn from(err: http::header::InvalidHeaderValue) -> Self {
        RustletteError::request_error(format!("Invalid header value: {}", err))
    }
}

impl From<http::header::InvalidHeaderName> for RustletteError {
    fn from(err: http::header::InvalidHeaderName) -> Self {
        RustletteError::request_error(format!("Invalid header name: {}", err))
    }
}

impl From<http::method::InvalidMethod> for RustletteError {
    fn from(err: http::method::InvalidMethod) -> Self {
        RustletteError::request_error(format!("Invalid HTTP method: {}", err))
    }
}

impl From<http::status::InvalidStatusCode> for RustletteError {
    fn from(err: http::status::InvalidStatusCode) -> Self {
        RustletteError::response_error(format!("Invalid status code: {}", err))
    }
}

impl From<http::uri::InvalidUri> for RustletteError {
    fn from(err: http::uri::InvalidUri) -> Self {
        RustletteError::request_error(format!("Invalid URI: {}", err))
    }
}

/// Helper trait for converting Results to RustletteResult
pub trait IntoRustletteResult<T> {
    fn into_rustlette_result(self) -> RustletteResult<T>;
}

impl<T, E> IntoRustletteResult<T> for Result<T, E>
where
    E: Into<RustletteError>,
{
    fn into_rustlette_result(self) -> RustletteResult<T> {
        self.map_err(|e| e.into())
    }
}

/// Helper macro for creating errors
#[macro_export]
macro_rules! rustlette_error {
    ($error_type:ident, $($arg:tt)*) => {
        RustletteError::$error_type(format!($($arg)*))
    };
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_creation() {
        let err = RustletteError::routing_error("Route not found");
        assert_eq!(err.error_type, "RoutingError");
        assert_eq!(err.status_code, Some(404));
        assert!(err.message.contains("Route not found"));
    }

    #[test]
    fn test_error_display() {
        let err = RustletteError::validation_error("Invalid input");
        assert_eq!(format!("{}", err), "ValidationError: Invalid input");
    }

    #[test]
    fn test_error_conversion() {
        let json_err = serde_json::from_str::<serde_json::Value>("invalid json");
        assert!(json_err.is_err());

        let rustlette_err: RustletteError = json_err.unwrap_err().into();
        assert_eq!(rustlette_err.error_type, "RequestError");
        assert_eq!(rustlette_err.status_code, Some(400));
    }

    #[test]
    fn test_macro() {
        let err = rustlette_error!(routing_error, "No route for path: {}", "/api/v1/users");
        assert_eq!(err.error_type, "RoutingError");
        assert!(err.message.contains("/api/v1/users"));
    }
}
