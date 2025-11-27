//! Response handling for Rustlette
//!
//! This module implements response creation and handling with multiple response types
//! that mirror Starlette's response API.

use crate::error::{RustletteError, RustletteResult};
use crate::types::{Headers, StatusCode};
use bytes::Bytes;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict, PyString};
use serde_json::Value as JsonValue;
use std::collections::HashMap;

/// Background task to be executed after response is sent
#[derive(Debug, Clone)]
pub struct BackgroundTask {
    pub func: PyObject,
    pub args: Vec<PyObject>,
    pub kwargs: Option<HashMap<String, PyObject>>,
}

impl BackgroundTask {
    pub fn new(
        func: PyObject,
        args: Vec<PyObject>,
        kwargs: Option<HashMap<String, PyObject>>,
    ) -> Self {
        Self { func, args, kwargs }
    }
}

/// Main response object that mirrors Starlette's Response API
#[derive(Debug, Clone)]
#[pyclass]
pub struct RustletteResponse {
    #[pyo3(get, set)]
    pub status_code: u16,
    #[pyo3(get)]
    pub headers: Headers,
    #[pyo3(get, set)]
    pub media_type: Option<String>,

    // Internal fields
    body: Option<Bytes>,
    background: Option<BackgroundTask>,
    charset: String,
}

#[pymethods]
impl RustletteResponse {
    #[new]
    #[pyo3(signature = (content=None, status_code=200, headers=None, media_type=None, background=None))]
    pub fn new(
        content: Option<PyObject>,
        status_code: Option<u16>,
        headers: Option<&PyDict>,
        media_type: Option<String>,
        background: Option<PyObject>,
    ) -> PyResult<Self> {
        let status_code = status_code.unwrap_or(200);

        let mut response_headers = if let Some(headers_dict) = headers {
            Headers::from_dict(
                Python::with_gil(|py| py.get_type::<Headers>()),
                headers_dict,
            )?
        } else {
            Headers::new()
        };

        let body = if let Some(content) = content {
            Python::with_gil(|py| {
                if let Ok(string_content) = content.extract::<String>(py) {
                    Some(Bytes::from(string_content.into_bytes()))
                } else if let Ok(bytes_content) = content.downcast::<PyBytes>(py) {
                    Some(Bytes::copy_from_slice(bytes_content.as_bytes()))
                } else {
                    // Try to convert to string
                    let string_repr = content.str(py)?.extract::<String>()?;
                    Some(Bytes::from(string_repr.into_bytes()))
                }
            })?
        } else {
            None
        };

        // Set default content-type if not provided and we have a media_type
        if let Some(ref mt) = media_type {
            if !response_headers.contains("content-type") {
                response_headers.set("content-type", mt);
            }
        }

        // Set content-length if we have body content
        if let Some(ref body) = body {
            response_headers.set("content-length", &body.len().to_string());
        }

        let background_task = background.map(|bg| {
            Python::with_gil(|py| {
                if bg.hasattr(py, "__call__").unwrap_or(false) {
                    BackgroundTask::new(bg, vec![], None)
                } else {
                    // Assume it's a BackgroundTask object
                    BackgroundTask::new(bg, vec![], None)
                }
            })
        });

        Ok(Self {
            status_code,
            headers: response_headers,
            media_type,
            body,
            background: background_task,
            charset: "utf-8".to_string(),
        })
    }

    /// Get the response body as bytes
    pub fn body(&self, py: Python) -> PyResult<PyObject> {
        match &self.body {
            Some(body) => Ok(PyBytes::new(py, body).into()),
            None => Ok(PyBytes::new(py, &[]).into()),
        }
    }

    /// Set the response body
    pub fn set_body(&mut self, content: PyObject) -> PyResult<()> {
        Python::with_gil(|py| {
            let body = if let Ok(string_content) = content.extract::<String>(py) {
                Bytes::from(string_content.into_bytes())
            } else if let Ok(bytes_content) = content.downcast::<PyBytes>(py) {
                Bytes::copy_from_slice(bytes_content.as_bytes())
            } else {
                let string_repr = content.str(py)?.extract::<String>()?;
                Bytes::from(string_repr.into_bytes())
            };

            // Update content-length
            self.headers.set("content-length", &body.len().to_string());
            self.body = Some(body);
            Ok(())
        })
    }

    /// Get the response body as text
    pub fn text(&self) -> PyResult<String> {
        match &self.body {
            Some(body) => String::from_utf8(body.to_vec()).map_err(|_| {
                pyo3::exceptions::PyUnicodeDecodeError::new_err(
                    "Response body contains invalid UTF-8",
                )
            }),
            None => Ok(String::new()),
        }
    }

    /// Set a cookie
    pub fn set_cookie(
        &mut self,
        name: &str,
        value: &str,
        max_age: Option<i32>,
        expires: Option<&str>,
        path: Option<&str>,
        domain: Option<&str>,
        secure: Option<bool>,
        httponly: Option<bool>,
        samesite: Option<&str>,
    ) -> PyResult<()> {
        let mut cookie = format!("{}={}", name, value);

        if let Some(max_age) = max_age {
            cookie.push_str(&format!("; Max-Age={}", max_age));
        }

        if let Some(expires) = expires {
            cookie.push_str(&format!("; Expires={}", expires));
        }

        if let Some(path) = path {
            cookie.push_str(&format!("; Path={}", path));
        }

        if let Some(domain) = domain {
            cookie.push_str(&format!("; Domain={}", domain));
        }

        if secure.unwrap_or(false) {
            cookie.push_str("; Secure");
        }

        if httponly.unwrap_or(false) {
            cookie.push_str("; HttpOnly");
        }

        if let Some(samesite) = samesite {
            cookie.push_str(&format!("; SameSite={}", samesite));
        }

        self.headers.add("set-cookie", &cookie);
        Ok(())
    }

    /// Delete a cookie
    pub fn delete_cookie(
        &mut self,
        name: &str,
        path: Option<&str>,
        domain: Option<&str>,
    ) -> PyResult<()> {
        let mut cookie = format!(
            "{}=; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT",
            name
        );

        if let Some(path) = path {
            cookie.push_str(&format!("; Path={}", path));
        }

        if let Some(domain) = domain {
            cookie.push_str(&format!("; Domain={}", domain));
        }

        self.headers.add("set-cookie", &cookie);
        Ok(())
    }

    /// Get the content length
    #[getter]
    pub fn content_length(&self) -> Option<usize> {
        self.body.as_ref().map(|b| b.len())
    }

    /// Check if the response is successful (2xx status code)
    #[getter]
    pub fn is_success(&self) -> bool {
        (200..300).contains(&self.status_code)
    }

    /// Check if the response is an error (4xx or 5xx status code)
    #[getter]
    pub fn is_error(&self) -> bool {
        self.status_code >= 400
    }

    /// Get the charset
    #[getter]
    pub fn charset(&self) -> String {
        self.charset.clone()
    }

    /// Set the charset
    #[setter]
    pub fn set_charset(&mut self, charset: String) {
        self.charset = charset;

        // Update content-type header if it exists
        if let Some(content_type) = self.headers.get("content-type") {
            if content_type.starts_with("text/") || content_type.contains("application/json") {
                let new_content_type = if content_type.contains("charset=") {
                    // Replace existing charset
                    let parts: Vec<&str> = content_type.split(';').collect();
                    format!("{}; charset={}", parts[0], self.charset)
                } else {
                    // Add charset
                    format!("{}; charset={}", content_type, self.charset)
                };
                self.headers.set("content-type", &new_content_type);
            }
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "Response(status_code={}, headers={})",
            self.status_code,
            self.headers.len()
        )
    }
}

impl RustletteResponse {
    /// Get the raw body bytes
    pub fn raw_body(&self) -> Option<&Bytes> {
        self.body.as_ref()
    }

    /// Get the background task
    pub fn background_task(&self) -> Option<&BackgroundTask> {
        self.background.as_ref()
    }

    /// Create response from raw components
    pub fn from_raw(status_code: u16, headers: Headers, body: Option<Bytes>) -> Self {
        Self {
            status_code,
            headers,
            media_type: None,
            body,
            background: None,
            charset: "utf-8".to_string(),
        }
    }
}

/// JSON response
#[derive(Debug, Clone)]
#[pyclass(extends=RustletteResponse)]
pub struct JSONResponse;

#[pymethods]
impl JSONResponse {
    #[new]
    #[pyo3(signature = (content, status_code=200, headers=None, media_type=None, background=None))]
    pub fn new(
        content: PyObject,
        status_code: Option<u16>,
        headers: Option<&PyDict>,
        media_type: Option<String>,
        background: Option<PyObject>,
    ) -> PyResult<(Self, RustletteResponse)> {
        let media_type = media_type.unwrap_or_else(|| "application/json".to_string());

        // Convert Python object to JSON string
        let json_content = Python::with_gil(|py| python_to_json(py, &content))?;

        let json_string = serde_json::to_string(&json_content).map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!("Failed to serialize JSON: {}", e))
        })?;

        let response = RustletteResponse::new(
            Some(json_string.into_py(Python::with_gil(|py| py))),
            status_code,
            headers,
            Some(media_type),
            background,
        )?;

        Ok((Self, response))
    }
}

/// HTML response
#[derive(Debug, Clone)]
#[pyclass(extends=RustletteResponse)]
pub struct HTMLResponse;

#[pymethods]
impl HTMLResponse {
    #[new]
    #[pyo3(signature = (content, status_code=200, headers=None, media_type=None, background=None))]
    pub fn new(
        content: PyObject,
        status_code: Option<u16>,
        headers: Option<&PyDict>,
        media_type: Option<String>,
        background: Option<PyObject>,
    ) -> PyResult<(Self, RustletteResponse)> {
        let media_type = media_type.unwrap_or_else(|| "text/html; charset=utf-8".to_string());

        let response = RustletteResponse::new(
            Some(content),
            status_code,
            headers,
            Some(media_type),
            background,
        )?;

        Ok((Self, response))
    }
}

/// Plain text response
#[derive(Debug, Clone)]
#[pyclass(extends=RustletteResponse)]
pub struct PlainTextResponse;

#[pymethods]
impl PlainTextResponse {
    #[new]
    #[pyo3(signature = (content, status_code=200, headers=None, media_type=None, background=None))]
    pub fn new(
        content: PyObject,
        status_code: Option<u16>,
        headers: Option<&PyDict>,
        media_type: Option<String>,
        background: Option<PyObject>,
    ) -> PyResult<(Self, RustletteResponse)> {
        let media_type = media_type.unwrap_or_else(|| "text/plain; charset=utf-8".to_string());

        let response = RustletteResponse::new(
            Some(content),
            status_code,
            headers,
            Some(media_type),
            background,
        )?;

        Ok((Self, response))
    }
}

/// Redirect response
#[derive(Debug, Clone)]
#[pyclass(extends=RustletteResponse)]
pub struct RedirectResponse;

#[pymethods]
impl RedirectResponse {
    #[new]
    #[pyo3(signature = (url, status_code=302, headers=None, background=None))]
    pub fn new(
        url: String,
        status_code: Option<u16>,
        headers: Option<&PyDict>,
        background: Option<PyObject>,
    ) -> PyResult<(Self, RustletteResponse)> {
        let status_code = status_code.unwrap_or(302);

        // Validate status code for redirects
        if ![301, 302, 303, 307, 308].contains(&status_code) {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Invalid redirect status code: {}",
                status_code
            )));
        }

        let mut response_headers = if let Some(headers_dict) = headers {
            Headers::from_dict(
                Python::with_gil(|py| py.get_type::<Headers>()),
                headers_dict,
            )?
        } else {
            Headers::new()
        };

        response_headers.set("location", &url);

        let response = RustletteResponse {
            status_code,
            headers: response_headers,
            media_type: None,
            body: None,
            background: background.map(|bg| BackgroundTask::new(bg, vec![], None)),
            charset: "utf-8".to_string(),
        };

        Ok((Self, response))
    }
}

/// File response for serving static files
#[derive(Debug, Clone)]
#[pyclass(extends=RustletteResponse)]
pub struct FileResponse;

#[pymethods]
impl FileResponse {
    #[new]
    #[pyo3(signature = (path, status_code=200, headers=None, media_type=None, filename=None, background=None))]
    pub fn new(
        path: String,
        status_code: Option<u16>,
        headers: Option<&PyDict>,
        media_type: Option<String>,
        filename: Option<String>,
        background: Option<PyObject>,
    ) -> PyResult<(Self, RustletteResponse)> {
        // Read file content
        let file_content = std::fs::read(&path).map_err(|e| {
            pyo3::exceptions::PyFileNotFoundError::new_err(format!(
                "Failed to read file '{}': {}",
                path, e
            ))
        })?;

        let media_type = media_type.unwrap_or_else(|| guess_media_type(&path));

        let mut response_headers = if let Some(headers_dict) = headers {
            Headers::from_dict(
                Python::with_gil(|py| py.get_type::<Headers>()),
                headers_dict,
            )?
        } else {
            Headers::new()
        };

        // Set content-disposition if filename is provided
        if let Some(filename) = filename {
            response_headers.set(
                "content-disposition",
                &format!("attachment; filename=\"{}\"", filename),
            );
        }

        let response = RustletteResponse {
            status_code: status_code.unwrap_or(200),
            headers: response_headers,
            media_type: Some(media_type),
            body: Some(Bytes::from(file_content)),
            background: background.map(|bg| BackgroundTask::new(bg, vec![], None)),
            charset: "utf-8".to_string(),
        };

        Ok((Self, response))
    }
}

/// Streaming response for large content
#[derive(Debug, Clone)]
#[pyclass(extends=RustletteResponse)]
pub struct StreamingResponse;

#[pymethods]
impl StreamingResponse {
    #[new]
    #[pyo3(signature = (content, status_code=200, headers=None, media_type=None, background=None))]
    pub fn new(
        content: PyObject, // Should be an iterator/generator
        status_code: Option<u16>,
        headers: Option<&PyDict>,
        media_type: Option<String>,
        background: Option<PyObject>,
    ) -> PyResult<(Self, RustletteResponse)> {
        let media_type = media_type.unwrap_or_else(|| "application/octet-stream".to_string());

        // For now, we'll collect the iterator into bytes
        // In a full implementation, this would support true streaming
        let body_content = Python::with_gil(|py| {
            let mut chunks = Vec::new();

            // Try to iterate over the content
            if let Ok(iter) = content.iter(py) {
                for item in iter {
                    let item = item?;
                    if let Ok(chunk) = item.extract::<String>() {
                        chunks.extend_from_slice(chunk.as_bytes());
                    } else if let Ok(chunk) = item.downcast::<PyBytes>() {
                        chunks.extend_from_slice(chunk.as_bytes());
                    }
                }
            } else {
                // Fallback: try to convert directly to string or bytes
                if let Ok(string_content) = content.extract::<String>() {
                    chunks.extend_from_slice(string_content.as_bytes());
                } else if let Ok(bytes_content) = content.downcast::<PyBytes>() {
                    chunks.extend_from_slice(bytes_content.as_bytes());
                }
            }

            Ok::<Vec<u8>, PyErr>(chunks)
        })?;

        let response = RustletteResponse {
            status_code: status_code.unwrap_or(200),
            headers: if let Some(headers_dict) = headers {
                Headers::from_dict(
                    Python::with_gil(|py| py.get_type::<Headers>()),
                    headers_dict,
                )?
            } else {
                Headers::new()
            },
            media_type: Some(media_type),
            body: Some(Bytes::from(body_content)),
            background: background.map(|bg| BackgroundTask::new(bg, vec![], None)),
            charset: "utf-8".to_string(),
        };

        Ok((Self, response))
    }
}

/// Convert Python object to JSON value
fn python_to_json(py: Python, obj: &PyObject) -> PyResult<JsonValue> {
    if obj.is_none(py) {
        Ok(JsonValue::Null)
    } else if let Ok(b) = obj.extract::<bool>(py) {
        Ok(JsonValue::Bool(b))
    } else if let Ok(i) = obj.extract::<i64>(py) {
        Ok(JsonValue::Number(serde_json::Number::from(i)))
    } else if let Ok(f) = obj.extract::<f64>(py) {
        if let Some(n) = serde_json::Number::from_f64(f) {
            Ok(JsonValue::Number(n))
        } else {
            Ok(JsonValue::Null)
        }
    } else if let Ok(s) = obj.extract::<String>(py) {
        Ok(JsonValue::String(s))
    } else if let Ok(list) = obj.downcast::<pyo3::types::PyList>(py) {
        let mut vec = Vec::new();
        for item in list.iter() {
            vec.push(python_to_json(py, &item.into())?);
        }
        Ok(JsonValue::Array(vec))
    } else if let Ok(dict) = obj.downcast::<pyo3::types::PyDict>(py) {
        let mut map = serde_json::Map::new();
        for (key, value) in dict.iter() {
            let key_str = key.extract::<String>()?;
            map.insert(key_str, python_to_json(py, &value.into())?);
        }
        Ok(JsonValue::Object(map))
    } else {
        // Fallback: convert to string
        let string_repr = obj.str(py)?.extract::<String>()?;
        Ok(JsonValue::String(string_repr))
    }
}

/// Guess media type from file extension
fn guess_media_type(path: &str) -> String {
    let extension = std::path::Path::new(path)
        .extension()
        .and_then(|ext| ext.to_str())
        .unwrap_or("");

    match extension.to_lowercase().as_str() {
        "html" | "htm" => "text/html",
        "css" => "text/css",
        "js" => "application/javascript",
        "json" => "application/json",
        "xml" => "application/xml",
        "pdf" => "application/pdf",
        "png" => "image/png",
        "jpg" | "jpeg" => "image/jpeg",
        "gif" => "image/gif",
        "svg" => "image/svg+xml",
        "ico" => "image/x-icon",
        "txt" => "text/plain",
        "csv" => "text/csv",
        "zip" => "application/zip",
        "tar" => "application/x-tar",
        "gz" => "application/gzip",
        "mp3" => "audio/mpeg",
        "mp4" => "video/mp4",
        "avi" => "video/x-msvideo",
        "mov" => "video/quicktime",
        _ => "application/octet-stream",
    }
    .to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_response_creation() {
        Python::with_gil(|py| {
            let response = RustletteResponse::new(
                Some("Hello, World!".to_object(py)),
                Some(200),
                None,
                Some("text/plain".to_string()),
                None,
            )
            .unwrap();

            assert_eq!(response.status_code, 200);
            assert_eq!(response.text().unwrap(), "Hello, World!");
            assert_eq!(response.media_type, Some("text/plain".to_string()));
        });
    }

    #[test]
    fn test_json_response() {
        Python::with_gil(|py| {
            let data = py.eval("{'name': 'John', 'age': 30}", None, None).unwrap();
            let (_, response) =
                JSONResponse::new(data.into(), Some(200), None, None, None).unwrap();

            assert_eq!(response.status_code, 200);
            assert!(response
                .headers
                .get("content-type")
                .unwrap()
                .contains("application/json"));
        });
    }

    #[test]
    fn test_redirect_response() {
        Python::with_gil(|py| {
            let (_, response) =
                RedirectResponse::new("https://example.com".to_string(), Some(302), None, None)
                    .unwrap();

            assert_eq!(response.status_code, 302);
            assert_eq!(
                response.headers.get("location"),
                Some("https://example.com".to_string())
            );
        });
    }

    #[test]
    fn test_cookie_setting() {
        Python::with_gil(|py| {
            let mut response =
                RustletteResponse::new(Some("Test".to_object(py)), None, None, None, None).unwrap();

            response
                .set_cookie(
                    "session_id",
                    "abc123",
                    Some(3600),
                    None,
                    Some("/"),
                    None,
                    Some(true),
                    Some(true),
                    Some("Strict"),
                )
                .unwrap();

            let cookies = response.headers.get_list("set-cookie");
            assert!(!cookies.is_empty());
            assert!(cookies[0].contains("session_id=abc123"));
            assert!(cookies[0].contains("Max-Age=3600"));
            assert!(cookies[0].contains("Secure"));
            assert!(cookies[0].contains("HttpOnly"));
        });
    }

    #[test]
    fn test_media_type_guessing() {
        assert_eq!(guess_media_type("test.html"), "text/html");
        assert_eq!(guess_media_type("test.json"), "application/json");
        assert_eq!(guess_media_type("test.png"), "image/png");
        assert_eq!(guess_media_type("test.unknown"), "application/octet-stream");
    }
}
