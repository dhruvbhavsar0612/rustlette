//! Request handling for Rustlette
//!
//! This module implements request parsing and handling with lazy loading
//! and a Starlette-compatible API.

use crate::error::{RustletteError, RustletteResult};
use crate::types::{HTTPMethod, Headers, QueryParams};
use bytes::Bytes;
use http::HeaderMap;
use pyo3::prelude::*;
use pyo3::types::PyType;
use pyo3::types::{PyBytes, PyDict};
use serde_json::Value as JsonValue;
use std::collections::HashMap;
use std::sync::Arc;
use url::Url;

/// Request state for storing arbitrary data
#[derive(Debug, Clone)]
pub struct RequestState {
    data: HashMap<String, PyObject>,
}

impl RequestState {
    pub fn new() -> Self {
        Self {
            data: HashMap::new(),
        }
    }

    pub fn get(&self, key: &str) -> Option<&PyObject> {
        self.data.get(key)
    }

    pub fn set(&mut self, key: String, value: PyObject) {
        self.data.insert(key, value);
    }

    pub fn remove(&mut self, key: &str) -> Option<PyObject> {
        self.data.remove(key)
    }

    pub fn contains(&self, key: &str) -> bool {
        self.data.contains_key(key)
    }

    pub fn keys(&self) -> Vec<&String> {
        self.data.keys().collect()
    }
}

impl Default for RequestState {
    fn default() -> Self {
        Self::new()
    }
}

/// Main request object that mirrors Starlette's Request API
#[derive(Debug, Clone)]
#[pyclass]
pub struct RustletteRequest {
    #[pyo3(get)]
    pub method: HTTPMethod,
    #[pyo3(get)]
    pub url: String,
    #[pyo3(get)]
    pub headers: Headers,
    #[pyo3(get)]
    pub query_params: QueryParams,
    #[pyo3(get)]
    pub path_params: HashMap<String, PyObject>,

    // Internal fields
    body: Option<Bytes>,
    parsed_url: Option<Url>,
    json_cache: Option<JsonValue>,
    form_cache: Option<HashMap<String, String>>,
    state: RequestState,
    client_info: Option<ClientInfo>,

    // Raw HTTP data
    raw_headers: HeaderMap,
    raw_body: Option<Bytes>,
}

/// Client connection information
#[derive(Debug, Clone)]
pub struct ClientInfo {
    pub host: String,
    pub port: u16,
    pub scheme: String,
}

#[pymethods]
impl RustletteRequest {
    #[new]
    pub fn new(
        method: String,
        url: String,
        headers: Option<&PyDict>,
        body: Option<&PyBytes>,
        path_params: Option<HashMap<String, PyObject>>,
    ) -> PyResult<Self> {
        let method: HTTPMethod = method.parse().map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!("Invalid HTTP method: {}", e))
        })?;

        let parsed_url = Url::parse(&url)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid URL: {}", e)))?;

        let query_params = QueryParams::from_query_string(parsed_url.query().unwrap_or(""));

        let headers = if let Some(headers_dict) = headers {
            Headers::from_dict_ref(headers_dict)?
        } else {
            Headers::new()
        };

        let body = body.map(|b| Bytes::copy_from_slice(b.as_bytes()));
        let path_params = path_params.unwrap_or_default();

        Ok(Self {
            method,
            url: url.clone(),
            headers: headers.clone(),
            query_params,
            path_params,
            body: body.clone(),
            parsed_url: Some(parsed_url),
            json_cache: None,
            form_cache: None,
            state: RequestState::new(),
            client_info: None,
            raw_headers: headers.into(),
            raw_body: body,
        })
    }

    /// Create a request from raw HTTP components
    #[classmethod]
    fn from_http_request(
        _cls: &PyType,
        method: String,
        uri: String,
        headers: &PyDict,
        body: Option<&PyBytes>,
    ) -> PyResult<Self> {
        Self::new(method, uri, Some(headers), body, None)
    }

    /// Get the request URL as a parsed URL object
    #[getter]
    pub fn parsed_url(&mut self) -> PyResult<String> {
        if self.parsed_url.is_none() {
            let parsed = Url::parse(&self.url).map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(format!("Invalid URL: {}", e))
            })?;
            self.parsed_url = Some(parsed);
        }
        Ok(self.url.clone())
    }

    /// Get the request scheme (http/https)
    #[getter]
    pub fn scheme(&mut self) -> PyResult<String> {
        if let Some(ref url) = self.parsed_url {
            Ok(url.scheme().to_string())
        } else {
            let parsed = Url::parse(&self.url).map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(format!("Invalid URL: {}", e))
            })?;
            let scheme = parsed.scheme().to_string();
            self.parsed_url = Some(parsed);
            Ok(scheme)
        }
    }

    /// Get the request hostname
    #[getter]
    pub fn hostname(&mut self) -> PyResult<Option<String>> {
        if let Some(ref url) = self.parsed_url {
            Ok(url.host_str().map(|s| s.to_string()))
        } else {
            let parsed = Url::parse(&self.url).map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(format!("Invalid URL: {}", e))
            })?;
            let hostname = parsed.host_str().map(|s| s.to_string());
            self.parsed_url = Some(parsed);
            Ok(hostname)
        }
    }

    /// Get the request port
    #[getter]
    pub fn port(&mut self) -> PyResult<Option<u16>> {
        if let Some(ref url) = self.parsed_url {
            Ok(url.port())
        } else {
            let parsed = Url::parse(&self.url).map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(format!("Invalid URL: {}", e))
            })?;
            let port = parsed.port();
            self.parsed_url = Some(parsed);
            Ok(port)
        }
    }

    /// Get the request path
    #[getter]
    pub fn path(&mut self) -> PyResult<String> {
        if let Some(ref url) = self.parsed_url {
            Ok(url.path().to_string())
        } else {
            let parsed = Url::parse(&self.url).map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(format!("Invalid URL: {}", e))
            })?;
            let path = parsed.path().to_string();
            self.parsed_url = Some(parsed);
            Ok(path)
        }
    }

    /// Get the raw request body as bytes
    pub fn body(&self) -> Option<&[u8]> {
        self.body.as_ref().map(|b| b.as_ref())
    }

    /// Get the request body as a Python bytes object
    pub fn body_bytes(&self, py: Python) -> PyResult<PyObject> {
        match &self.body {
            Some(body) => Ok(PyBytes::new(py, body).into()),
            None => Ok(PyBytes::new(py, &[]).into()),
        }
    }

    /// Get the request body as text
    pub fn text(&self) -> PyResult<String> {
        match &self.body {
            Some(body) => String::from_utf8(body.to_vec()).map_err(|_| {
                pyo3::exceptions::PyUnicodeDecodeError::new_err(
                    "Request body contains invalid UTF-8",
                )
            }),
            None => Ok(String::new()),
        }
    }

    /// Parse the request body as JSON
    pub fn json(&mut self) -> PyResult<PyObject> {
        if self.json_cache.is_none() {
            let body_text = self.text()?;
            if body_text.is_empty() {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "Request body is empty",
                ));
            }

            let json_value: JsonValue = serde_json::from_str(&body_text).map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(format!("Invalid JSON: {}", e))
            })?;

            self.json_cache = Some(json_value);
        }

        Python::with_gil(|py| {
            if let Some(ref json_value) = self.json_cache {
                json_to_python(py, json_value)
            } else {
                Ok(py.None())
            }
        })
    }

    /// Parse the request body as form data
    pub fn form(&mut self) -> PyResult<PyObject> {
        if self.form_cache.is_none() {
            let body_text = self.text()?;
            let mut form_data = HashMap::new();

            for pair in body_text.split('&') {
                if let Some((key, value)) = pair.split_once('=') {
                    let key = urlencoding::decode(key).unwrap_or_default().to_string();
                    let value = urlencoding::decode(value).unwrap_or_default().to_string();
                    form_data.insert(key, value);
                }
            }

            self.form_cache = Some(form_data);
        }

        Python::with_gil(|py| {
            if let Some(ref form_data) = self.form_cache {
                let dict = PyDict::new(py);
                for (key, value) in form_data {
                    dict.set_item(key, value)?;
                }
                Ok(dict.into())
            } else {
                Ok(PyDict::new(py).into())
            }
        })
    }

    /// Check if the request accepts a specific content type
    pub fn accepts(&self, content_type: &str) -> bool {
        if let Some(accept_header) = self.headers.get("accept") {
            accept_header.contains(content_type) || accept_header.contains("*/*")
        } else {
            false
        }
    }

    /// Get a specific header value
    pub fn header(&self, name: &str) -> Option<String> {
        self.headers.get(name)
    }

    /// Get cookies from the request
    pub fn cookies(&self) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let dict = PyDict::new(py);

            if let Some(cookie_header) = self.headers.get("cookie") {
                for cookie in cookie_header.split(';') {
                    if let Some((name, value)) = cookie.trim().split_once('=') {
                        dict.set_item(name.trim(), value.trim())?;
                    }
                }
            }

            Ok(dict.into())
        })
    }

    /// Get the client IP address
    #[getter]
    pub fn client(&self) -> Option<String> {
        // Try various headers for client IP
        self.headers
            .get("x-forwarded-for")
            .or_else(|| self.headers.get("x-real-ip"))
            .or_else(|| self.headers.get("x-client-ip"))
            .or_else(|| {
                if let Some(ref client_info) = self.client_info {
                    Some(client_info.host.clone())
                } else {
                    None
                }
            })
    }

    /// Check if the request is secure (HTTPS)
    #[getter]
    pub fn is_secure(&mut self) -> PyResult<bool> {
        let scheme = self.scheme()?;
        Ok(scheme == "https")
    }

    /// Get or set request state
    pub fn state_get(&self, key: &str) -> Option<PyObject> {
        self.state.get(key).cloned()
    }

    pub fn state_set(&mut self, key: String, value: PyObject) {
        self.state.set(key, value);
    }

    pub fn state_contains(&self, key: &str) -> bool {
        self.state.contains(key)
    }

    /// Get the content type
    #[getter]
    pub fn content_type(&self) -> Option<String> {
        self.headers.get("content-type")
    }

    /// Get the content length
    #[getter]
    pub fn content_length(&self) -> Option<usize> {
        self.headers
            .get("content-length")
            .and_then(|s| s.parse().ok())
    }

    /// Check if this is a JSON request
    #[getter]
    pub fn is_json(&self) -> bool {
        self.content_type()
            .map(|ct| ct.contains("application/json"))
            .unwrap_or(false)
    }

    /// Check if this is a form request
    #[getter]
    pub fn is_form(&self) -> bool {
        self.content_type()
            .map(|ct| ct.contains("application/x-www-form-urlencoded"))
            .unwrap_or(false)
    }

    /// Get the user agent
    #[getter]
    pub fn user_agent(&self) -> Option<String> {
        self.headers.get("user-agent")
    }

    /// Get the referrer
    #[getter]
    pub fn referrer(&self) -> Option<String> {
        self.headers.get("referer")
    }

    /// Get the authorization header
    #[getter]
    pub fn authorization(&self) -> Option<String> {
        self.headers.get("authorization")
    }

    /// Create a copy of the request with modifications
    pub fn replace(
        &self,
        method: Option<String>,
        url: Option<String>,
        headers: Option<&PyDict>,
        body: Option<&PyBytes>,
        path_params: Option<HashMap<String, PyObject>>,
    ) -> PyResult<Self> {
        let new_method = if let Some(m) = method {
            m.parse().map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(format!("Invalid HTTP method: {}", e))
            })?
        } else {
            self.method
        };

        let url_changed = url.is_some();
        let new_url = url.unwrap_or_else(|| self.url.clone());

        let new_headers = if let Some(h) = headers {
            Headers::from_dict_ref(h)?
        } else {
            self.headers.clone()
        };

        let new_body = if let Some(b) = body {
            Some(Bytes::copy_from_slice(b.as_bytes()))
        } else {
            self.body.clone()
        };

        let new_path_params = path_params.unwrap_or_else(|| self.path_params.clone());

        Ok(Self {
            method: new_method,
            url: new_url.clone(),
            headers: new_headers.clone(),
            query_params: if url_changed {
                let parsed = Url::parse(&new_url).map_err(|e| {
                    pyo3::exceptions::PyValueError::new_err(format!("Invalid URL: {}", e))
                })?;
                QueryParams::from_query_string(parsed.query().unwrap_or(""))
            } else {
                self.query_params.clone()
            },
            path_params: new_path_params,
            body: new_body.clone(),
            parsed_url: None, // Will be re-parsed when needed
            json_cache: None,
            form_cache: None,
            state: self.state.clone(),
            client_info: self.client_info.clone(),
            raw_headers: new_headers.into(),
            raw_body: new_body,
        })
    }

    fn __repr__(&self) -> String {
        format!("Request(method='{}', url='{}')", self.method, self.url)
    }
}

impl RustletteRequest {
    /// Create a new request from Hyper request parts
    pub fn from_hyper_request(
        method: http::Method,
        uri: http::Uri,
        headers: HeaderMap,
        body: Option<Bytes>,
    ) -> RustletteResult<Self> {
        let method = HTTPMethod::from(method);
        let url = uri.to_string();
        let headers = Headers::from(&headers);

        let parsed_url = Url::parse(&url)?;
        let query_params = QueryParams::from_query_string(parsed_url.query().unwrap_or(""));

        Ok(Self {
            method,
            url,
            headers: headers.clone(),
            query_params,
            path_params: HashMap::new(),
            body,
            parsed_url: Some(parsed_url),
            json_cache: None,
            form_cache: None,
            state: RequestState::new(),
            client_info: None,
            raw_headers: headers.into(),
            raw_body: None,
        })
    }

    /// Set client connection information
    pub fn set_client_info(&mut self, host: String, port: u16, scheme: String) {
        self.client_info = Some(ClientInfo { host, port, scheme });
    }

    /// Set path parameters (used by router)
    pub fn set_path_params(&mut self, params: HashMap<String, PyObject>) {
        self.path_params = params;
    }
}

/// Convert a serde_json::Value to a Python object
fn json_to_python(py: Python, value: &JsonValue) -> PyResult<PyObject> {
    match value {
        JsonValue::Null => Ok(py.None()),
        JsonValue::Bool(b) => Ok(b.to_object(py)),
        JsonValue::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(i.to_object(py))
            } else if let Some(f) = n.as_f64() {
                Ok(f.to_object(py))
            } else {
                Ok(n.to_string().to_object(py))
            }
        }
        JsonValue::String(s) => Ok(s.to_object(py)),
        JsonValue::Array(arr) => {
            let list = pyo3::types::PyList::empty(py);
            for item in arr {
                list.append(json_to_python(py, item)?)?;
            }
            Ok(list.into())
        }
        JsonValue::Object(obj) => {
            let dict = PyDict::new(py);
            for (key, value) in obj {
                dict.set_item(key, json_to_python(py, value)?)?;
            }
            Ok(dict.into())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_request_creation() {
        Python::with_gil(|py| {
            let request = RustletteRequest::new(
                "GET".to_string(),
                "https://example.com/users?page=1".to_string(),
                None,
                None,
                None,
            )
            .unwrap();

            assert_eq!(request.method, HTTPMethod::GET);
            assert_eq!(request.url, "https://example.com/users?page=1");
            assert_eq!(request.query_params.get("page"), Some(&"1".to_string()));
        });
    }

    #[test]
    fn test_request_json_parsing() {
        Python::with_gil(|py| {
            let json_body = r#"{"name": "John", "age": 30}"#;
            let body_bytes = PyBytes::new(py, json_body.as_bytes());

            let mut request = RustletteRequest::new(
                "POST".to_string(),
                "https://example.com/users".to_string(),
                None,
                Some(body_bytes),
                None,
            )
            .unwrap();

            let json_data = request.json().unwrap();
            // Verify the JSON was parsed correctly
            assert!(json_data.is_instance_of::<PyDict>(py));
        });
    }

    #[test]
    fn test_request_url_parsing() {
        Python::with_gil(|py| {
            let mut request = RustletteRequest::new(
                "GET".to_string(),
                "https://example.com:8080/users/123?sort=name".to_string(),
                None,
                None,
                None,
            )
            .unwrap();

            assert_eq!(request.scheme().unwrap(), "https");
            assert_eq!(request.hostname().unwrap(), Some("example.com".to_string()));
            assert_eq!(request.port().unwrap(), Some(8080));
            assert_eq!(request.path().unwrap(), "/users/123");
        });
    }

    #[test]
    fn test_request_headers() {
        Python::with_gil(|py| {
            let headers_dict = PyDict::new(py);
            headers_dict
                .set_item("content-type", "application/json")
                .unwrap();
            headers_dict
                .set_item("authorization", "Bearer token123")
                .unwrap();

            let request = RustletteRequest::new(
                "POST".to_string(),
                "https://example.com/api".to_string(),
                Some(headers_dict),
                None,
                None,
            )
            .unwrap();

            assert_eq!(request.content_type(), Some("application/json".to_string()));
            assert_eq!(request.authorization(), Some("Bearer token123".to_string()));
            assert!(request.is_json());
        });
    }
}
