//! ASGI compatibility layer for Rustlette
//!
//! This module implements ASGI 3.0 compatibility, allowing Rustlette applications
//! to be deployed on ASGI servers like Uvicorn, Gunicorn, and Hypercorn.

use crate::error::{RustletteError, RustletteResult};
use crate::request::RustletteRequest;
use crate::response::RustletteResponse;
use crate::types::{HTTPMethod, Headers};
use bytes::Bytes;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple};
use std::collections::HashMap;
use std::sync::Arc;

/// ASGI message types
#[derive(Debug, Clone)]
pub enum ASGIMessage {
    HTTPRequestStart {
        method: String,
        path: String,
        query_string: Vec<u8>,
        headers: Vec<(Vec<u8>, Vec<u8>)>,
        scheme: String,
        server: Option<(String, u16)>,
        client: Option<(String, u16)>,
    },
    HTTPRequestBody {
        body: Vec<u8>,
        more_body: bool,
    },
    HTTPResponseStart {
        status: u16,
        headers: Vec<(Vec<u8>, Vec<u8>)>,
    },
    HTTPResponseBody {
        body: Vec<u8>,
        more_body: bool,
    },
    HTTPDisconnect,
    WebSocketConnect,
    WebSocketAccept {
        subprotocol: Option<String>,
        headers: Vec<(Vec<u8>, Vec<u8>)>,
    },
    WebSocketReceive {
        bytes: Option<Vec<u8>>,
        text: Option<String>,
    },
    WebSocketSend {
        bytes: Option<Vec<u8>>,
        text: Option<String>,
    },
    WebSocketDisconnect {
        code: u16,
    },
}

/// ASGI scope information
#[derive(Debug, Clone)]
pub struct ASGIScope {
    pub scope_type: String,
    pub asgi_version: String,
    pub http_version: String,
    pub method: String,
    pub scheme: String,
    pub path: String,
    pub raw_path: Vec<u8>,
    pub query_string: Vec<u8>,
    pub root_path: String,
    pub headers: Vec<(Vec<u8>, Vec<u8>)>,
    pub server: Option<(String, u16)>,
    pub client: Option<(String, u16)>,
    pub extensions: HashMap<String, PyObject>,
}

impl ASGIScope {
    /// Create scope from Python dict
    pub fn from_python(scope: &PyDict) -> PyResult<Self> {
        let scope_type: String = scope
            .get_item("type")?
            .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("Missing 'type' in scope"))?
            .extract()?;

        let asgi_version: String = scope
            .get_item("asgi")?
            .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("Missing 'asgi' in scope"))?
            .get_item("version")?
            .extract()?;

        let http_version: String = scope
            .get_item("http_version")?
            .unwrap_or_else(|| "1.1".into_py(scope.py()))
            .extract()?;

        let method: String = scope
            .get_item("method")?
            .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("Missing 'method' in scope"))?
            .extract()?;

        let scheme: String = scope
            .get_item("scheme")?
            .unwrap_or_else(|| "http".into_py(scope.py()))
            .extract()?;

        let path: String = scope
            .get_item("path")?
            .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("Missing 'path' in scope"))?
            .extract()?;

        let raw_path: Vec<u8> = scope
            .get_item("raw_path")?
            .unwrap_or_else(|| path.as_bytes().into_py(scope.py()))
            .extract()?;

        let query_string: Vec<u8> = scope
            .get_item("query_string")?
            .unwrap_or_else(|| Vec::<u8>::new().into_py(scope.py()))
            .extract()?;

        let root_path: String = scope
            .get_item("root_path")?
            .unwrap_or_else(|| "".into_py(scope.py()))
            .extract()?;

        let headers: Vec<(Vec<u8>, Vec<u8>)> = scope
            .get_item("headers")?
            .unwrap_or_else(|| Vec::<(Vec<u8>, Vec<u8>)>::new().into_py(scope.py()))
            .extract()?;

        let server: Option<(String, u16)> =
            scope.get_item("server")?.map(|s| s.extract()).transpose()?;

        let client: Option<(String, u16)> =
            scope.get_item("client")?.map(|c| c.extract()).transpose()?;

        let extensions = if let Some(ext) = scope.get_item("extensions")? {
            if let Ok(ext_dict) = ext.downcast::<PyDict>() {
                let mut extensions = HashMap::new();
                for (key, value) in ext_dict.iter() {
                    let key: String = key.extract()?;
                    extensions.insert(key, value.into());
                }
                extensions
            } else {
                HashMap::new()
            }
        } else {
            HashMap::new()
        };

        Ok(Self {
            scope_type,
            asgi_version,
            http_version,
            method,
            scheme,
            path,
            raw_path,
            query_string,
            root_path,
            headers,
            server,
            client,
            extensions,
        })
    }

    /// Convert to Python dict
    pub fn to_python(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);

        dict.set_item("type", &self.scope_type)?;

        let asgi_dict = PyDict::new(py);
        asgi_dict.set_item("version", &self.asgi_version)?;
        dict.set_item("asgi", asgi_dict)?;

        dict.set_item("http_version", &self.http_version)?;
        dict.set_item("method", &self.method)?;
        dict.set_item("scheme", &self.scheme)?;
        dict.set_item("path", &self.path)?;
        dict.set_item("raw_path", &self.raw_path)?;
        dict.set_item("query_string", &self.query_string)?;
        dict.set_item("root_path", &self.root_path)?;
        dict.set_item("headers", &self.headers)?;

        if let Some(ref server) = self.server {
            dict.set_item("server", server)?;
        }

        if let Some(ref client) = self.client {
            dict.set_item("client", client)?;
        }

        if !self.extensions.is_empty() {
            let ext_dict = PyDict::new(py);
            for (key, value) in &self.extensions {
                ext_dict.set_item(key, value)?;
            }
            dict.set_item("extensions", ext_dict)?;
        }

        Ok(dict.into())
    }

    /// Build URL from scope
    pub fn build_url(&self) -> String {
        let mut url = format!("{}://{}", self.scheme, self.build_host());
        url.push_str(&self.path);

        if !self.query_string.is_empty() {
            url.push('?');
            url.push_str(&String::from_utf8_lossy(&self.query_string));
        }

        url
    }

    /// Build host from server info
    fn build_host(&self) -> String {
        if let Some((host, port)) = &self.server {
            let default_port = match self.scheme.as_str() {
                "https" => 443,
                "http" => 80,
                _ => 80,
            };

            if *port == default_port {
                host.clone()
            } else {
                format!("{}:{}", host, port)
            }
        } else {
            "localhost".to_string()
        }
    }
}

/// ASGI receive callable wrapper
#[derive(Debug, Clone)]
pub struct ASGIReceive {
    receive: PyObject,
}

impl ASGIReceive {
    pub fn new(receive: PyObject) -> Self {
        Self { receive }
    }

    /// Receive the next ASGI message
    pub async fn next(&self) -> PyResult<ASGIMessage> {
        Python::with_gil(|py| {
            let result = self.receive.call0(py)?;

            // If this is a coroutine, await it
            if result.hasattr(py, "__await__")? {
                // For now, we'll treat this as a regular dict
                // In a full implementation, this would properly await the coroutine
                self.parse_message(result.downcast::<PyDict>()?)
            } else {
                self.parse_message(result.downcast::<PyDict>()?)
            }
        })
    }

    fn parse_message(&self, message: &PyDict) -> PyResult<ASGIMessage> {
        let msg_type: String = message
            .get_item("type")?
            .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("Missing 'type' in message"))?
            .extract()?;

        match msg_type.as_str() {
            "http.request" => {
                let body: Vec<u8> = message
                    .get_item("body")?
                    .unwrap_or_else(|| Vec::<u8>::new().into_py(message.py()))
                    .extract()?;

                let more_body: bool = message
                    .get_item("more_body")?
                    .unwrap_or_else(|| false.into_py(message.py()))
                    .extract()?;

                Ok(ASGIMessage::HTTPRequestBody { body, more_body })
            }
            "http.disconnect" => Ok(ASGIMessage::HTTPDisconnect),
            "websocket.connect" => Ok(ASGIMessage::WebSocketConnect),
            "websocket.receive" => {
                let bytes: Option<Vec<u8>> = message
                    .get_item("bytes")?
                    .map(|b| b.extract())
                    .transpose()?;

                let text: Option<String> =
                    message.get_item("text")?.map(|t| t.extract()).transpose()?;

                Ok(ASGIMessage::WebSocketReceive { bytes, text })
            }
            "websocket.disconnect" => {
                let code: u16 = message
                    .get_item("code")?
                    .unwrap_or_else(|| 1000u16.into_py(message.py()))
                    .extract()?;

                Ok(ASGIMessage::WebSocketDisconnect { code })
            }
            _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Unknown ASGI message type: {}",
                msg_type
            ))),
        }
    }
}

/// ASGI send callable wrapper
#[derive(Debug, Clone)]
pub struct ASGISend {
    send: PyObject,
}

impl ASGISend {
    pub fn new(send: PyObject) -> Self {
        Self { send }
    }

    /// Send an ASGI message
    pub async fn send(&self, message: ASGIMessage) -> PyResult<()> {
        Python::with_gil(|py| {
            let msg_dict = self.message_to_python(py, message)?;
            let result = self.send.call1(py, (msg_dict,))?;

            // If this is a coroutine, we should await it
            // For now, we'll just return the result
            Ok(())
        })
    }

    fn message_to_python(&self, py: Python, message: ASGIMessage) -> PyResult<PyObject> {
        let dict = PyDict::new(py);

        match message {
            ASGIMessage::HTTPResponseStart { status, headers } => {
                dict.set_item("type", "http.response.start")?;
                dict.set_item("status", status)?;
                dict.set_item("headers", headers)?;
            }
            ASGIMessage::HTTPResponseBody { body, more_body } => {
                dict.set_item("type", "http.response.body")?;
                dict.set_item("body", body)?;
                dict.set_item("more_body", more_body)?;
            }
            ASGIMessage::WebSocketAccept {
                subprotocol,
                headers,
            } => {
                dict.set_item("type", "websocket.accept")?;
                if let Some(subprotocol) = subprotocol {
                    dict.set_item("subprotocol", subprotocol)?;
                }
                dict.set_item("headers", headers)?;
            }
            ASGIMessage::WebSocketSend { bytes, text } => {
                dict.set_item("type", "websocket.send")?;
                if let Some(bytes) = bytes {
                    dict.set_item("bytes", bytes)?;
                }
                if let Some(text) = text {
                    dict.set_item("text", text)?;
                }
            }
            _ => {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "Cannot send this message type",
                ));
            }
        }

        Ok(dict.into())
    }
}

/// Main ASGI application wrapper
#[derive(Debug, Clone)]
#[pyclass]
pub struct ASGIApp {
    app: PyObject,
}

#[pymethods]
impl ASGIApp {
    #[new]
    pub fn new(app: PyObject) -> Self {
        Self { app }
    }

    /// ASGI application callable
    #[pyo3(name = "__call__")]
    pub fn call(&self, scope: &PyDict, receive: PyObject, send: PyObject) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            // Parse the ASGI scope
            let asgi_scope = ASGIScope::from_python(scope)?;

            match asgi_scope.scope_type.as_str() {
                "http" => self.handle_http_request(py, asgi_scope, receive, send),
                "websocket" => self.handle_websocket(py, asgi_scope, receive, send),
                "lifespan" => self.handle_lifespan(py, asgi_scope, receive, send),
                _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
                    "Unsupported ASGI scope type: {}",
                    asgi_scope.scope_type
                ))),
            }
        })
    }

    fn __repr__(&self) -> String {
        "ASGIApp".to_string()
    }
}

impl ASGIApp {
    fn handle_http_request(
        &self,
        py: Python,
        scope: ASGIScope,
        receive: PyObject,
        send: PyObject,
    ) -> PyResult<PyObject> {
        // Create future/coroutine for async execution
        pyo3_asyncio::tokio::future_into_py(py, async move {
            let asgi_receive = ASGIReceive::new(receive);
            let asgi_send = ASGISend::new(send);

            // Collect the request body
            let mut body_parts = Vec::new();
            loop {
                match asgi_receive.next().await? {
                    ASGIMessage::HTTPRequestBody { body, more_body } => {
                        body_parts.extend_from_slice(&body);
                        if !more_body {
                            break;
                        }
                    }
                    ASGIMessage::HTTPDisconnect => {
                        // Client disconnected
                        return Ok(());
                    }
                    _ => {
                        return Err(pyo3::exceptions::PyRuntimeError::new_err(
                            "Unexpected message type in HTTP request",
                        ));
                    }
                }
            }

            // Build the Rustlette request
            let request = self.build_request_from_scope(scope, body_parts)?;

            // Process the request through the app
            let response = self.process_request(request).await?;

            // Send the response
            self.send_response(asgi_send, response).await?;

            Ok(())
        })
    }

    fn handle_websocket(
        &self,
        py: Python,
        _scope: ASGIScope,
        _receive: PyObject,
        _send: PyObject,
    ) -> PyResult<PyObject> {
        // WebSocket support would be implemented here
        pyo3_asyncio::tokio::future_into_py(py, async move {
            Err(pyo3::exceptions::PyNotImplementedError::new_err(
                "WebSocket support not yet implemented",
            ))
        })
    }

    fn handle_lifespan(
        &self,
        py: Python,
        _scope: ASGIScope,
        receive: PyObject,
        send: PyObject,
    ) -> PyResult<PyObject> {
        pyo3_asyncio::tokio::future_into_py(py, async move {
            let asgi_receive = ASGIReceive::new(receive);
            let asgi_send = ASGISend::new(send);

            // Handle lifespan protocol
            loop {
                match asgi_receive.next().await? {
                    ASGIMessage::HTTPDisconnect => {
                        // Lifespan startup
                        // TODO: Call app startup handlers

                        let response = Python::with_gil(|py| {
                            let dict = PyDict::new(py);
                            dict.set_item("type", "lifespan.startup.complete")?;
                            Ok::<PyObject, PyErr>(dict.into())
                        })?;

                        asgi_send
                            .send
                            .call1(Python::with_gil(|py| py), (response,))?;
                    }
                    _ => break,
                }
            }

            Ok(())
        })
    }

    fn build_request_from_scope(
        &self,
        scope: ASGIScope,
        body: Vec<u8>,
    ) -> PyResult<RustletteRequest> {
        Python::with_gil(|py| {
            // Convert headers
            let headers_dict = PyDict::new(py);
            for (name, value) in scope.headers {
                let name_str = String::from_utf8_lossy(&name);
                let value_str = String::from_utf8_lossy(&value);
                headers_dict.set_item(name_str.as_ref(), value_str.as_ref())?;
            }

            // Convert body
            let body_bytes = if body.is_empty() {
                None
            } else {
                Some(pyo3::types::PyBytes::new(py, &body))
            };

            // Build URL
            let url = scope.build_url();

            RustletteRequest::new(scope.method, url, Some(headers_dict), body_bytes, None)
        })
    }

    async fn process_request(&self, request: RustletteRequest) -> PyResult<RustletteResponse> {
        Python::with_gil(|py| {
            // Call the Rustlette app with the request
            let result = self.app.call1(py, (request,))?;

            // Extract the response
            result.extract::<RustletteResponse>()
        })
    }

    async fn send_response(
        &self,
        asgi_send: ASGISend,
        response: RustletteResponse,
    ) -> PyResult<()> {
        // Convert headers to ASGI format
        let mut headers = Vec::new();
        for key in response.headers.keys() {
            if let Some(value) = response.headers.get(&key) {
                headers.push((key.as_bytes().to_vec(), value.as_bytes().to_vec()));
            }
        }

        // Send response start
        asgi_send
            .send(ASGIMessage::HTTPResponseStart {
                status: response.status_code,
                headers,
            })
            .await?;

        // Send response body
        let body = response.raw_body().map(|b| b.to_vec()).unwrap_or_default();
        asgi_send
            .send(ASGIMessage::HTTPResponseBody {
                body,
                more_body: false,
            })
            .await?;

        Ok(())
    }
}

/// Helper functions for ASGI integration
pub mod asgi_helpers {
    use super::*;

    /// Create an ASGI app from a Rustlette app
    pub fn create_asgi_app(app: PyObject) -> ASGIApp {
        ASGIApp::new(app)
    }

    /// Validate ASGI scope
    pub fn validate_scope(scope: &PyDict) -> PyResult<()> {
        let scope_type: String = scope
            .get_item("type")?
            .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("Missing 'type' in scope"))?
            .extract()?;

        match scope_type.as_str() {
            "http" | "websocket" | "lifespan" => Ok(()),
            _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Invalid ASGI scope type: {}",
                scope_type
            ))),
        }
    }

    /// Convert Rustlette headers to ASGI format
    pub fn headers_to_asgi(headers: &Headers) -> Vec<(Vec<u8>, Vec<u8>)> {
        let mut asgi_headers = Vec::new();
        for key in headers.keys() {
            if let Some(value) = headers.get(&key) {
                asgi_headers.push((key.as_bytes().to_vec(), value.as_bytes().to_vec()));
            }
        }
        asgi_headers
    }

    /// Convert ASGI headers to Rustlette format
    pub fn headers_from_asgi(headers: &[(Vec<u8>, Vec<u8>)]) -> Headers {
        let mut rustlette_headers = Headers::new();
        for (name, value) in headers {
            let name_str = String::from_utf8_lossy(name);
            let value_str = String::from_utf8_lossy(value);
            rustlette_headers.set(&name_str, &value_str);
        }
        rustlette_headers
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::types::PyDict;

    #[test]
    fn test_asgi_scope_parsing() {
        Python::with_gil(|py| {
            let scope = PyDict::new(py);
            scope.set_item("type", "http").unwrap();

            let asgi_dict = PyDict::new(py);
            asgi_dict.set_item("version", "3.0").unwrap();
            scope.set_item("asgi", asgi_dict).unwrap();

            scope.set_item("method", "GET").unwrap();
            scope.set_item("path", "/test").unwrap();

            let parsed_scope = ASGIScope::from_python(scope).unwrap();
            assert_eq!(parsed_scope.scope_type, "http");
            assert_eq!(parsed_scope.method, "GET");
            assert_eq!(parsed_scope.path, "/test");
        });
    }

    #[test]
    fn test_asgi_app_creation() {
        Python::with_gil(|py| {
            let app_func = py
                .eval("lambda request: None", None, None)
                .unwrap()
                .to_object(py);

            let asgi_app = ASGIApp::new(app_func);
            assert_eq!(format!("{:?}", asgi_app).contains("ASGIApp"), true);
        });
    }

    #[test]
    fn test_header_conversion() {
        let headers = vec![
            (b"content-type".to_vec(), b"application/json".to_vec()),
            (b"authorization".to_vec(), b"Bearer token123".to_vec()),
        ];

        let rustlette_headers = asgi_helpers::headers_from_asgi(&headers);
        assert_eq!(
            rustlette_headers.get("content-type"),
            Some("application/json".to_string())
        );
        assert_eq!(
            rustlette_headers.get("authorization"),
            Some("Bearer token123".to_string())
        );

        let asgi_headers = asgi_helpers::headers_to_asgi(&rustlette_headers);
        assert_eq!(asgi_headers.len(), 2);
    }
}
