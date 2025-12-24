//! Core types for Rustlette
//!
//! This module defines the fundamental types used throughout the framework,
//! including HTTP methods, status codes, and headers.

use pyo3::prelude::*;
use pyo3::types::PyType;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fmt;
use std::str::FromStr;

/// HTTP methods supported by Rustlette
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[pyclass]
pub enum HTTPMethod {
    GET,
    POST,
    PUT,
    DELETE,
    PATCH,
    HEAD,
    OPTIONS,
    TRACE,
    CONNECT,
}

#[pymethods]
impl HTTPMethod {
    #[new]
    pub fn new(method: &str) -> PyResult<Self> {
        method.parse().map_err(|_| {
            pyo3::exceptions::PyValueError::new_err(format!("Invalid HTTP method: {}", method))
        })
    }

    fn __str__(&self) -> &'static str {
        match self {
            HTTPMethod::GET => "GET",
            HTTPMethod::POST => "POST",
            HTTPMethod::PUT => "PUT",
            HTTPMethod::DELETE => "DELETE",
            HTTPMethod::PATCH => "PATCH",
            HTTPMethod::HEAD => "HEAD",
            HTTPMethod::OPTIONS => "OPTIONS",
            HTTPMethod::TRACE => "TRACE",
            HTTPMethod::CONNECT => "CONNECT",
        }
    }

    fn __repr__(&self) -> String {
        format!("HTTPMethod.{}", self.__str__())
    }

    fn __eq__(&self, other: &Self) -> bool {
        self == other
    }

    fn __hash__(&self) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        let mut hasher = DefaultHasher::new();
        self.hash(&mut hasher);
        hasher.finish()
    }

    /// Check if this method is safe (GET, HEAD, OPTIONS, TRACE)
    #[getter]
    pub fn is_safe(&self) -> bool {
        matches!(
            self,
            HTTPMethod::GET | HTTPMethod::HEAD | HTTPMethod::OPTIONS | HTTPMethod::TRACE
        )
    }

    /// Check if this method is idempotent
    #[getter]
    pub fn is_idempotent(&self) -> bool {
        matches!(
            self,
            HTTPMethod::GET
                | HTTPMethod::HEAD
                | HTTPMethod::PUT
                | HTTPMethod::DELETE
                | HTTPMethod::OPTIONS
                | HTTPMethod::TRACE
        )
    }

    /// Check if this method typically has a request body
    #[getter]
    pub fn has_body(&self) -> bool {
        matches!(self, HTTPMethod::POST | HTTPMethod::PUT | HTTPMethod::PATCH)
    }
}

impl fmt::Display for HTTPMethod {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}",
            match self {
                HTTPMethod::GET => "GET",
                HTTPMethod::POST => "POST",
                HTTPMethod::PUT => "PUT",
                HTTPMethod::DELETE => "DELETE",
                HTTPMethod::PATCH => "PATCH",
                HTTPMethod::HEAD => "HEAD",
                HTTPMethod::OPTIONS => "OPTIONS",
                HTTPMethod::TRACE => "TRACE",
                HTTPMethod::CONNECT => "CONNECT",
            }
        )
    }
}

impl FromStr for HTTPMethod {
    type Err = crate::error::RustletteError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_uppercase().as_str() {
            "GET" => Ok(HTTPMethod::GET),
            "POST" => Ok(HTTPMethod::POST),
            "PUT" => Ok(HTTPMethod::PUT),
            "DELETE" => Ok(HTTPMethod::DELETE),
            "PATCH" => Ok(HTTPMethod::PATCH),
            "HEAD" => Ok(HTTPMethod::HEAD),
            "OPTIONS" => Ok(HTTPMethod::OPTIONS),
            "TRACE" => Ok(HTTPMethod::TRACE),
            "CONNECT" => Ok(HTTPMethod::CONNECT),
            _ => Err(crate::error::RustletteError::request_error(format!(
                "Unsupported HTTP method: {}",
                s
            ))),
        }
    }
}

impl From<http::Method> for HTTPMethod {
    fn from(method: http::Method) -> Self {
        match method {
            http::Method::GET => HTTPMethod::GET,
            http::Method::POST => HTTPMethod::POST,
            http::Method::PUT => HTTPMethod::PUT,
            http::Method::DELETE => HTTPMethod::DELETE,
            http::Method::PATCH => HTTPMethod::PATCH,
            http::Method::HEAD => HTTPMethod::HEAD,
            http::Method::OPTIONS => HTTPMethod::OPTIONS,
            http::Method::TRACE => HTTPMethod::TRACE,
            http::Method::CONNECT => HTTPMethod::CONNECT,
            _ => HTTPMethod::GET, // Default fallback
        }
    }
}

impl From<HTTPMethod> for http::Method {
    fn from(method: HTTPMethod) -> Self {
        match method {
            HTTPMethod::GET => http::Method::GET,
            HTTPMethod::POST => http::Method::POST,
            HTTPMethod::PUT => http::Method::PUT,
            HTTPMethod::DELETE => http::Method::DELETE,
            HTTPMethod::PATCH => http::Method::PATCH,
            HTTPMethod::HEAD => http::Method::HEAD,
            HTTPMethod::OPTIONS => http::Method::OPTIONS,
            HTTPMethod::TRACE => http::Method::TRACE,
            HTTPMethod::CONNECT => http::Method::CONNECT,
        }
    }
}

/// HTTP status codes
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[pyclass]
pub struct StatusCode {
    #[pyo3(get)]
    pub code: u16,
}

#[pymethods]
impl StatusCode {
    #[new]
    pub fn new(code: u16) -> PyResult<Self> {
        if (100..=599).contains(&code) {
            Ok(Self { code })
        } else {
            Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Invalid status code: {}. Must be between 100 and 599",
                code
            )))
        }
    }

    fn __str__(&self) -> String {
        format!("{}", self.code)
    }

    fn __repr__(&self) -> String {
        format!("StatusCode({})", self.code)
    }

    fn __eq__(&self, other: &Self) -> bool {
        self.code == other.code
    }

    fn __hash__(&self) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        let mut hasher = DefaultHasher::new();
        self.code.hash(&mut hasher);
        hasher.finish()
    }

    /// Get the reason phrase for this status code
    #[getter]
    pub fn phrase(&self) -> &'static str {
        match self.code {
            100 => "Continue",
            101 => "Switching Protocols",
            200 => "OK",
            201 => "Created",
            202 => "Accepted",
            204 => "No Content",
            301 => "Moved Permanently",
            302 => "Found",
            304 => "Not Modified",
            400 => "Bad Request",
            401 => "Unauthorized",
            403 => "Forbidden",
            404 => "Not Found",
            405 => "Method Not Allowed",
            409 => "Conflict",
            422 => "Unprocessable Entity",
            500 => "Internal Server Error",
            501 => "Not Implemented",
            502 => "Bad Gateway",
            503 => "Service Unavailable",
            _ => "Unknown",
        }
    }

    /// Check if this is an informational status (1xx)
    #[getter]
    pub fn is_informational(&self) -> bool {
        (100..200).contains(&self.code)
    }

    /// Check if this is a successful status (2xx)
    #[getter]
    pub fn is_success(&self) -> bool {
        (200..300).contains(&self.code)
    }

    /// Check if this is a redirection status (3xx)
    #[getter]
    pub fn is_redirection(&self) -> bool {
        (300..400).contains(&self.code)
    }

    /// Check if this is a client error status (4xx)
    #[getter]
    pub fn is_client_error(&self) -> bool {
        (400..500).contains(&self.code)
    }

    /// Check if this is a server error status (5xx)
    #[getter]
    pub fn is_server_error(&self) -> bool {
        (500..600).contains(&self.code)
    }

    /// Check if this is an error status (4xx or 5xx)
    #[getter]
    pub fn is_error(&self) -> bool {
        self.is_client_error() || self.is_server_error()
    }

    // Common status codes as class attributes
    #[classattr]
    fn OK() -> Self {
        Self { code: 200 }
    }

    #[classattr]
    fn CREATED() -> Self {
        Self { code: 201 }
    }

    #[classattr]
    fn NO_CONTENT() -> Self {
        Self { code: 204 }
    }

    #[classattr]
    fn BAD_REQUEST() -> Self {
        Self { code: 400 }
    }

    #[classattr]
    fn UNAUTHORIZED() -> Self {
        Self { code: 401 }
    }

    #[classattr]
    fn FORBIDDEN() -> Self {
        Self { code: 403 }
    }

    #[classattr]
    fn NOT_FOUND() -> Self {
        Self { code: 404 }
    }

    #[classattr]
    fn METHOD_NOT_ALLOWED() -> Self {
        Self { code: 405 }
    }

    #[classattr]
    fn UNPROCESSABLE_ENTITY() -> Self {
        Self { code: 422 }
    }

    #[classattr]
    fn INTERNAL_SERVER_ERROR() -> Self {
        Self { code: 500 }
    }
}

impl From<u16> for StatusCode {
    fn from(code: u16) -> Self {
        Self { code }
    }
}

impl From<StatusCode> for u16 {
    fn from(status: StatusCode) -> Self {
        status.code
    }
}

impl From<http::StatusCode> for StatusCode {
    fn from(status: http::StatusCode) -> Self {
        Self {
            code: status.as_u16(),
        }
    }
}

impl From<StatusCode> for http::StatusCode {
    fn from(status: StatusCode) -> Self {
        http::StatusCode::from_u16(status.code).unwrap_or(http::StatusCode::INTERNAL_SERVER_ERROR)
    }
}

/// HTTP headers container
#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct Headers {
    #[pyo3(get)]
    headers: HashMap<String, Vec<String>>,
}

#[pymethods]
impl Headers {
    #[new]
    pub fn new() -> Self {
        Self {
            headers: HashMap::new(),
        }
    }

    /// Create headers from a Python dict
    #[classmethod]
    pub fn from_dict(_cls: &PyType, dict: &PyAny) -> PyResult<Self> {
        let mut headers = HashMap::new();

        if let Ok(py_dict) = dict.downcast::<pyo3::types::PyDict>() {
            for (key, value) in py_dict.iter() {
                let key: String = key.extract()?;
                let key = key.to_lowercase(); // Normalize header names

                if let Ok(string_value) = value.extract::<String>() {
                    headers.insert(key, vec![string_value]);
                } else if let Ok(list_value) = value.extract::<Vec<String>>() {
                    headers.insert(key, list_value);
                }
            }
        }

        Ok(Self { headers })
    }

    /// Get a header value
    pub fn get(&self, name: &str) -> Option<String> {
        self.headers
            .get(&name.to_lowercase())
            .and_then(|values| values.first())
            .cloned()
    }

    /// Get all values for a header
    pub fn get_list(&self, name: &str) -> Vec<String> {
        self.headers
            .get(&name.to_lowercase())
            .cloned()
            .unwrap_or_default()
    }

    /// Set a header value (replaces existing)
    pub fn set(&mut self, name: &str, value: &str) {
        self.headers
            .insert(name.to_lowercase(), vec![value.to_string()]);
    }

    /// Add a header value (appends to existing)
    pub fn add(&mut self, name: &str, value: &str) {
        let key = name.to_lowercase();
        self.headers
            .entry(key)
            .or_insert_with(Vec::new)
            .push(value.to_string());
    }

    /// Remove a header
    pub fn remove(&mut self, name: &str) -> Option<Vec<String>> {
        self.headers.remove(&name.to_lowercase())
    }

    /// Check if a header exists
    pub fn contains(&self, name: &str) -> bool {
        self.headers.contains_key(&name.to_lowercase())
    }

    /// Get all header names
    pub fn keys(&self) -> Vec<String> {
        self.headers.keys().cloned().collect()
    }

    /// Get number of headers
    pub fn len(&self) -> usize {
        self.headers.len()
    }

    /// Check if headers are empty
    pub fn is_empty(&self) -> bool {
        self.headers.is_empty()
    }

    /// Convert to Python dict
    pub fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = pyo3::types::PyDict::new(py);
        for (key, values) in &self.headers {
            if values.len() == 1 {
                dict.set_item(key, &values[0])?;
            } else {
                dict.set_item(key, values)?;
            }
        }
        Ok(dict.into())
    }

    /// Clear all headers
    pub fn clear(&mut self) {
        self.headers.clear();
    }

    fn __len__(&self) -> usize {
        self.len()
    }

    fn __contains__(&self, name: &str) -> bool {
        self.contains(name)
    }

    fn __getitem__(&self, name: &str) -> PyResult<String> {
        self.get(name).ok_or_else(|| {
            pyo3::exceptions::PyKeyError::new_err(format!("Header '{}' not found", name))
        })
    }

    fn __setitem__(&mut self, name: &str, value: &str) {
        self.set(name, value);
    }

    fn __delitem__(&mut self, name: &str) -> PyResult<()> {
        self.remove(name).ok_or_else(|| {
            pyo3::exceptions::PyKeyError::new_err(format!("Header '{}' not found", name))
        })?;
        Ok(())
    }

    fn __iter__(slf: PyRef<Self>) -> PyResult<HeadersIterator> {
        Ok(HeadersIterator {
            keys: slf.headers.keys().cloned().collect(),
            index: 0,
        })
    }

    fn __repr__(&self) -> String {
        format!("Headers({})", self.headers.len())
    }
}

// Additional methods outside pymethods
impl Headers {
    /// Create headers from a Python dict reference (no PyType needed)
    pub fn from_dict_ref(dict: &PyAny) -> PyResult<Self> {
        let mut headers = HashMap::new();

        if let Ok(py_dict) = dict.downcast::<pyo3::types::PyDict>() {
            for (key, value) in py_dict.iter() {
                let key: String = key.extract()?;
                let key = key.to_lowercase(); // Normalize header names

                if let Ok(string_value) = value.extract::<String>() {
                    headers.insert(key, vec![string_value]);
                } else if let Ok(list_value) = value.extract::<Vec<String>>() {
                    headers.insert(key, list_value);
                }
            }
        }

        Ok(Self { headers })
    }
}

impl Default for Headers {
    fn default() -> Self {
        Self::new()
    }
}

impl From<&http::HeaderMap> for Headers {
    fn from(header_map: &http::HeaderMap) -> Self {
        let mut headers = HashMap::new();

        for (name, value) in header_map.iter() {
            let name = name.as_str().to_lowercase();
            let value = value.to_str().unwrap_or("").to_string();

            headers.entry(name).or_insert_with(Vec::new).push(value);
        }

        Self { headers }
    }
}

impl From<Headers> for http::HeaderMap {
    fn from(headers: Headers) -> Self {
        let mut header_map = http::HeaderMap::new();

        for (name, values) in headers.headers {
            if let Ok(header_name) = http::HeaderName::from_bytes(name.as_bytes()) {
                for value in values {
                    if let Ok(header_value) = http::HeaderValue::from_str(&value) {
                        header_map.append(&header_name, header_value);
                    }
                }
            }
        }

        header_map
    }
}

/// Iterator for Headers
#[pyclass]
pub struct HeadersIterator {
    keys: Vec<String>,
    index: usize,
}

#[pymethods]
impl HeadersIterator {
    fn __iter__(slf: PyRef<Self>) -> PyRef<Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<Self>) -> Option<String> {
        if slf.index < slf.keys.len() {
            let key = slf.keys[slf.index].clone();
            slf.index += 1;
            Some(key)
        } else {
            None
        }
    }
}

/// Query parameters container
#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct QueryParams {
    params: HashMap<String, Vec<String>>,
}

impl QueryParams {
    pub fn new() -> Self {
        Self {
            params: HashMap::new(),
        }
    }

    pub fn from_query_string(query: &str) -> Self {
        let mut params = HashMap::new();

        for pair in query.split('&') {
            if let Some((key, value)) = pair.split_once('=') {
                let key = urlencoding::decode(key).unwrap_or_default().to_string();
                let value = urlencoding::decode(value).unwrap_or_default().to_string();

                params.entry(key).or_insert_with(Vec::new).push(value);
            } else if !pair.is_empty() {
                let key = urlencoding::decode(pair).unwrap_or_default().to_string();
                params
                    .entry(key)
                    .or_insert_with(Vec::new)
                    .push(String::new());
            }
        }

        Self { params }
    }

    pub fn get(&self, name: &str) -> Option<&String> {
        self.params.get(name).and_then(|values| values.first())
    }

    pub fn get_list(&self, name: &str) -> Option<&Vec<String>> {
        self.params.get(name)
    }

    pub fn contains(&self, name: &str) -> bool {
        self.params.contains_key(name)
    }

    pub fn keys(&self) -> impl Iterator<Item = &String> {
        self.params.keys()
    }

    pub fn len(&self) -> usize {
        self.params.len()
    }

    pub fn is_empty(&self) -> bool {
        self.params.is_empty()
    }
}

impl Default for QueryParams {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_http_method() {
        let method = HTTPMethod::GET;
        assert_eq!(method.to_string(), "GET");
        assert!(method.is_safe());
        assert!(method.is_idempotent());
        assert!(!method.has_body());

        let method = HTTPMethod::POST;
        assert!(!method.is_safe());
        assert!(!method.is_idempotent());
        assert!(method.has_body());
    }

    #[test]
    fn test_status_code() {
        let status = StatusCode::new(200).unwrap();
        assert_eq!(status.code, 200);
        assert_eq!(status.phrase(), "OK");
        assert!(status.is_success());
        assert!(!status.is_error());

        let status = StatusCode::new(404).unwrap();
        assert!(status.is_client_error());
        assert!(status.is_error());
    }

    #[test]
    fn test_headers() {
        let mut headers = Headers::new();
        headers.set("content-type", "application/json");
        headers.add("accept", "application/json");
        headers.add("accept", "text/html");

        assert_eq!(
            headers.get("content-type"),
            Some("application/json".to_string())
        );
        assert_eq!(headers.get_list("accept").len(), 2);
        assert!(headers.contains("content-type"));
        assert!(!headers.contains("authorization"));
    }

    #[test]
    fn test_query_params() {
        let params = QueryParams::from_query_string("foo=bar&baz=qux&foo=quux");
        assert_eq!(params.get("foo"), Some(&"bar".to_string()));
        assert_eq!(params.get_list("foo").unwrap().len(), 2);
        assert_eq!(params.get("baz"), Some(&"qux".to_string()));
    }
}
