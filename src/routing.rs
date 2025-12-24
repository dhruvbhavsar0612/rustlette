//! Routing system for Rustlette
//!
//! This module implements an efficient routing system with trie-based path matching
//! and parameter extraction, designed to mirror Starlette's routing API.

use crate::error::{RustletteError, RustletteResult};
use crate::types::{HTTPMethod, QueryParams};
use pyo3::prelude::*;
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fmt;
use std::sync::Arc;

/// Path parameter converter types
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[pyclass]
pub enum PathConverter {
    /// String converter (default)
    Str,
    /// Integer converter
    Int,
    /// Float converter
    Float,
    /// Path converter (matches including slashes)
    Path,
    /// UUID converter
    UUID,
    /// Slug converter (alphanumeric + hyphens/underscores)
    Slug,
}

#[pymethods]
impl PathConverter {
    #[new]
    pub fn new(converter_type: &str) -> PyResult<Self> {
        match converter_type.to_lowercase().as_str() {
            "str" | "string" => Ok(PathConverter::Str),
            "int" | "integer" => Ok(PathConverter::Int),
            "float" => Ok(PathConverter::Float),
            "path" => Ok(PathConverter::Path),
            "uuid" => Ok(PathConverter::UUID),
            "slug" => Ok(PathConverter::Slug),
            _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Unknown path converter: {}",
                converter_type
            ))),
        }
    }

    fn __str__(&self) -> &'static str {
        match self {
            PathConverter::Str => "str",
            PathConverter::Int => "int",
            PathConverter::Float => "float",
            PathConverter::Path => "path",
            PathConverter::UUID => "uuid",
            PathConverter::Slug => "slug",
        }
    }

    fn __repr__(&self) -> String {
        format!("PathConverter.{}", self.__str__())
    }

    /// Get the regex pattern for this converter
    pub fn pattern(&self) -> &'static str {
        match self {
            PathConverter::Str => r"[^/]+",
            PathConverter::Int => r"-?\d+",
            PathConverter::Float => r"-?\d+(\.\d+)?",
            PathConverter::Path => r".+",
            PathConverter::UUID => r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            PathConverter::Slug => r"[-a-zA-Z0-9_]+",
        }
    }

    /// Convert a matched string to the appropriate Python type
    pub fn convert(&self, value: &str) -> PyResult<PyObject> {
        Python::with_gil(|py| match self {
            PathConverter::Str => Ok(value.to_object(py)),
            PathConverter::Int => value.parse::<i64>().map(|i| i.to_object(py)).map_err(|_| {
                pyo3::exceptions::PyValueError::new_err(format!(
                    "Cannot convert '{}' to integer",
                    value
                ))
            }),
            PathConverter::Float => value.parse::<f64>().map(|f| f.to_object(py)).map_err(|_| {
                pyo3::exceptions::PyValueError::new_err(format!(
                    "Cannot convert '{}' to float",
                    value
                ))
            }),
            PathConverter::Path => Ok(value.to_object(py)),
            PathConverter::UUID => {
                // Validate UUID format
                if uuid::Uuid::parse_str(value).is_ok() {
                    Ok(value.to_object(py))
                } else {
                    Err(pyo3::exceptions::PyValueError::new_err(format!(
                        "Invalid UUID format: {}",
                        value
                    )))
                }
            }
            PathConverter::Slug => Ok(value.to_object(py)),
        })
    }
}

/// Path parameter definition
#[derive(Debug, Clone)]
pub struct PathParam {
    pub name: String,
    pub converter: PathConverter,
    pub optional: bool,
}

impl PathParam {
    pub fn new(name: String, converter: PathConverter, optional: bool) -> Self {
        Self {
            name,
            converter,
            optional,
        }
    }
}

/// Compiled route pattern with extracted parameters
#[derive(Debug, Clone)]
pub struct CompiledRoute {
    pub pattern: Regex,
    pub params: Vec<PathParam>,
    pub path_template: String,
}

impl CompiledRoute {
    /// Compile a route pattern into a regex with parameter extraction
    pub fn compile(path: &str) -> RustletteResult<Self> {
        let mut pattern_str = String::new();
        let mut params = Vec::new();
        let mut chars = path.chars().peekable();
        let path_template = path.to_string();

        pattern_str.push('^');

        while let Some(ch) = chars.next() {
            match ch {
                '{' => {
                    // Parse parameter: {name:converter} or {name}
                    let mut param_str = String::new();
                    let mut brace_count = 1;

                    while let Some(ch) = chars.next() {
                        if ch == '{' {
                            brace_count += 1;
                        } else if ch == '}' {
                            brace_count -= 1;
                            if brace_count == 0 {
                                break;
                            }
                        }
                        param_str.push(ch);
                    }

                    let (name, converter) =
                        if let Some((name, converter_str)) = param_str.split_once(':') {
                            let converter = match converter_str {
                                "int" => PathConverter::Int,
                                "float" => PathConverter::Float,
                                "path" => PathConverter::Path,
                                "uuid" => PathConverter::UUID,
                                "slug" => PathConverter::Slug,
                                "str" | "" => PathConverter::Str,
                                _ => {
                                    return Err(RustletteError::routing_error(format!(
                                        "Unknown path converter: {}",
                                        converter_str
                                    )))
                                }
                            };
                            (name.to_string(), converter)
                        } else {
                            (param_str, PathConverter::Str)
                        };

                    // Add named capture group
                    pattern_str.push_str(&format!("(?P<{}>{})", name, converter.pattern()));
                    params.push(PathParam::new(name, converter, false));
                }
                '*' => {
                    // Wildcard parameter (path converter)
                    if let Some('{') = chars.peek() {
                        chars.next(); // consume '{'
                        let mut param_str = String::new();
                        while let Some(ch) = chars.next() {
                            if ch == '}' {
                                break;
                            }
                            param_str.push(ch);
                        }
                        pattern_str.push_str(&format!("(?P<{}>.+)", param_str));
                        params.push(PathParam::new(param_str, PathConverter::Path, false));
                    } else {
                        pattern_str.push_str(".*");
                    }
                }
                '.' | '+' | '?' | '^' | '$' | '(' | ')' | '[' | ']' | '|' | '\\' => {
                    // Escape regex special characters
                    pattern_str.push('\\');
                    pattern_str.push(ch);
                }
                _ => {
                    pattern_str.push(ch);
                }
            }
        }

        pattern_str.push('$');

        let pattern = Regex::new(&pattern_str).map_err(|e| {
            RustletteError::routing_error(format!("Invalid route pattern '{}': {}", path, e))
        })?;

        Ok(CompiledRoute {
            pattern,
            params,
            path_template,
        })
    }

    /// Match a path and extract parameters
    pub fn match_path(&self, path: &str) -> Option<HashMap<String, PyObject>> {
        self.pattern.captures(path).map(|captures| {
            let mut params = HashMap::new();
            Python::with_gil(|py| {
                for param in &self.params {
                    if let Some(matched) = captures.name(&param.name) {
                        if let Ok(converted) = param.converter.convert(matched.as_str()) {
                            params.insert(param.name.clone(), converted);
                        }
                    }
                }
            });
            params
        })
    }
}

/// A single route definition
#[derive(Debug, Clone)]
#[pyclass]
pub struct Route {
    #[pyo3(get)]
    pub path: String,
    #[pyo3(get)]
    pub methods: Vec<HTTPMethod>,
    #[pyo3(get)]
    pub name: Option<String>,
    #[pyo3(get)]
    pub include_in_schema: bool,
    pub compiled: CompiledRoute,
    pub handler: Option<PyObject>,
}

#[pymethods]
impl Route {
    #[new]
    #[pyo3(signature = (path, handler=None, methods=None, name=None, include_in_schema=true))]
    pub fn new(
        path: String,
        handler: Option<PyObject>,
        methods: Option<Vec<String>>,
        name: Option<String>,
        include_in_schema: Option<bool>,
    ) -> PyResult<Self> {
        let methods = if let Some(method_strs) = methods {
            method_strs
                .into_iter()
                .map(|m| m.parse())
                .collect::<Result<Vec<_>, _>>()
                .map_err(|e: crate::error::RustletteError| {
                    pyo3::exceptions::PyValueError::new_err(e.to_string())
                })?
        } else {
            vec![HTTPMethod::GET]
        };

        let compiled = CompiledRoute::compile(&path)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;

        Ok(Route {
            path,
            methods,
            name,
            include_in_schema: include_in_schema.unwrap_or(true),
            compiled,
            handler,
        })
    }

    fn __repr__(&self) -> String {
        format!(
            "Route(path='{}', methods={:?}, name={:?})",
            self.path, self.methods, self.name
        )
    }

    /// Check if this route matches the given method
    pub fn matches_method(&self, method: &HTTPMethod) -> bool {
        self.methods.contains(method)
    }

    /// Match this route against a path and method
    pub fn match_request(
        &self,
        path: &str,
        method: &HTTPMethod,
    ) -> Option<HashMap<String, PyObject>> {
        if self.matches_method(method) {
            self.compiled.match_path(path)
        } else {
            None
        }
    }

    /// Get the path template with parameter placeholders
    #[getter]
    pub fn path_template(&self) -> String {
        self.compiled.path_template.clone()
    }

    /// Generate a URL from this route with the given parameters
    pub fn url_for(&self, params: Option<HashMap<String, PyObject>>) -> PyResult<String> {
        let mut url = self.path.clone();

        if let Some(params) = params {
            Python::with_gil(|py| {
                for (key, value) in params {
                    let value_str: String = value.extract(py)?;
                    url = url.replace(&format!("{{{}}}", key), &value_str);
                    // Also handle typed parameters like {id:int}
                    for param in &self.compiled.params {
                        if param.name == key {
                            let pattern = format!("{{{}:{}}}", key, param.converter.__str__());
                            url = url.replace(&pattern, &value_str);
                        }
                    }
                }
                Ok::<(), PyErr>(())
            })?;
        }

        Ok(url)
    }
}

/// Route matching result
#[derive(Debug)]
#[pyclass]
pub struct RouteMatch {
    pub route: Arc<Route>,
    pub path_params: HashMap<String, PyObject>,
}

impl RouteMatch {
    pub fn new(route: Arc<Route>, path_params: HashMap<String, PyObject>) -> Self {
        Self { route, path_params }
    }
}

/// Router implementation using trie-based matching
#[derive(Debug)]
#[pyclass]
pub struct Router {
    routes: Vec<Arc<Route>>,
    route_map: HashMap<String, Arc<Route>>, // name -> route mapping
}

#[pymethods]
impl Router {
    #[new]
    pub fn new() -> Self {
        Self {
            routes: Vec::new(),
            route_map: HashMap::new(),
        }
    }

    /// Add a route to the router
    pub fn add_route(&mut self, route: Route) -> PyResult<()> {
        let route = Arc::new(route);

        // Add to name mapping if route has a name
        if let Some(ref name) = route.name {
            if self.route_map.contains_key(name) {
                return Err(pyo3::exceptions::PyValueError::new_err(format!(
                    "Route with name '{}' already exists",
                    name
                )));
            }
            self.route_map.insert(name.clone(), route.clone());
        }

        self.routes.push(route);
        Ok(())
    }

    /// Remove a route by index
    pub fn remove_route(&mut self, index: usize) -> PyResult<()> {
        if index >= self.routes.len() {
            return Err(pyo3::exceptions::PyIndexError::new_err(
                "Route index out of range",
            ));
        }

        let route = self.routes.remove(index);
        if let Some(ref name) = route.name {
            self.route_map.remove(name);
        }

        Ok(())
    }

    /// Match a request against all routes
    pub fn match_request(&self, path: &str, method: &str) -> Option<RouteMatch> {
        let method: HTTPMethod = match method.parse() {
            Ok(m) => m,
            Err(_) => return None,
        };

        for route in &self.routes {
            if let Some(path_params) = route.match_request(path, &method) {
                return Some(RouteMatch::new(route.clone(), path_params));
            }
        }

        None
    }

    /// Get number of routes
    #[getter]
    pub fn route_count(&self) -> usize {
        self.routes.len()
    }

    /// Check if router is empty
    pub fn is_empty(&self) -> bool {
        self.routes.is_empty()
    }

    /// Generate URL for a named route
    pub fn url_for(
        &self,
        name: &str,
        params: Option<HashMap<String, PyObject>>,
    ) -> PyResult<String> {
        if let Some(route) = self.route_map.get(name) {
            route.url_for(params)
        } else {
            Err(pyo3::exceptions::PyKeyError::new_err(format!(
                "No route named '{}'",
                name
            )))
        }
    }

    fn __len__(&self) -> usize {
        self.route_count()
    }

    fn __repr__(&self) -> String {
        format!("Router({} routes)", self.routes.len())
    }
}

// Internal methods not exposed to Python
impl Router {
    pub(crate) fn get_route(&self, name: &str) -> Option<Arc<Route>> {
        self.route_map.get(name).cloned()
    }

    pub(crate) fn routes_for_path(&self, path: &str) -> Vec<Arc<Route>> {
        self.routes
            .iter()
            .filter(|route| route.compiled.pattern.is_match(path))
            .cloned()
            .collect()
    }

    pub(crate) fn routes_for_method(&self, method: &HTTPMethod) -> Vec<Arc<Route>> {
        self.routes
            .iter()
            .filter(|route| route.matches_method(method))
            .cloned()
            .collect()
    }
}

impl Default for Router {
    fn default() -> Self {
        Self::new()
    }
}

/// Mount point for sub-applications
#[derive(Debug, Clone)]
pub struct Mount {
    pub path: String,
    pub app: PyObject,
    pub name: Option<String>,
}

impl Mount {
    pub fn new(path: String, app: PyObject, name: Option<String>) -> Self {
        Self { path, app, name }
    }
}

/// Host-based routing
#[derive(Debug, Clone)]
pub struct Host {
    pub host: String,
    pub app: PyObject,
    pub name: Option<String>,
}

impl Host {
    pub fn new(host: String, app: PyObject, name: Option<String>) -> Self {
        Self { host, app, name }
    }
}

/// WebSocket route (for future implementation)
#[derive(Debug, Clone)]
pub struct WebSocketRoute {
    pub path: String,
    pub endpoint: PyObject,
    pub name: Option<String>,
}

impl WebSocketRoute {
    pub fn new(path: String, endpoint: PyObject, name: Option<String>) -> Self {
        Self {
            path,
            endpoint,
            name,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_path_converter() {
        let converter = PathConverter::Int;
        assert_eq!(converter.pattern(), r"-?\d+");

        Python::with_gil(|py| {
            let result = converter.convert("123").unwrap();
            let value: i64 = result.extract(py).unwrap();
            assert_eq!(value, 123);
        });
    }

    #[test]
    fn test_compiled_route() {
        let route = CompiledRoute::compile("/users/{id:int}/posts/{slug}").unwrap();
        assert_eq!(route.params.len(), 2);
        assert_eq!(route.params[0].name, "id");
        assert_eq!(route.params[0].converter, PathConverter::Int);
        assert_eq!(route.params[1].name, "slug");
        assert_eq!(route.params[1].converter, PathConverter::Str);

        let params = route.match_path("/users/123/posts/hello-world");
        assert!(params.is_some());
        let params = params.unwrap();
        assert_eq!(params.len(), 2);
    }

    #[test]
    fn test_route_matching() {
        Python::with_gil(|py| {
            let route = Route::new(
                "/users/{id:int}".to_string(),
                None,
                Some(vec!["GET".to_string(), "POST".to_string()]),
                Some("user_detail".to_string()),
                None,
            )
            .unwrap();

            assert!(route.matches_method(&HTTPMethod::GET));
            assert!(route.matches_method(&HTTPMethod::POST));
            assert!(!route.matches_method(&HTTPMethod::DELETE));

            let params = route.match_request("/users/123", &HTTPMethod::GET);
            assert!(params.is_some());

            let params = route.match_request("/users/abc", &HTTPMethod::GET);
            assert!(params.is_none()); // Should fail because 'abc' is not an integer
        });
    }

    #[test]
    fn test_router() {
        Python::with_gil(|py| {
            let mut router = Router::new();

            let route1 = Route::new(
                "/users".to_string(),
                None,
                Some(vec!["GET".to_string()]),
                Some("users".to_string()),
                None,
            )
            .unwrap();

            let route2 = Route::new(
                "/users/{id:int}".to_string(),
                None,
                Some(vec!["GET".to_string()]),
                Some("user_detail".to_string()),
                None,
            )
            .unwrap();

            router.add_route(route1).unwrap();
            router.add_route(route2).unwrap();

            assert_eq!(router.len(), 2);

            let match_result = router.match_request("/users/123", "GET").unwrap();
            assert!(match_result.is_some());

            let route_match = match_result.unwrap();
            assert_eq!(route_match.route.name, Some("user_detail".to_string()));
            assert_eq!(route_match.path_params.len(), 1);
        });
    }

    #[test]
    fn test_url_generation() {
        Python::with_gil(|py| {
            let route = Route::new(
                "/users/{id:int}/posts/{slug}".to_string(),
                None,
                None,
                None,
                None,
            )
            .unwrap();

            let mut params = HashMap::new();
            params.insert("id".to_string(), 123i64.to_object(py));
            params.insert("slug".to_string(), "hello-world".to_object(py));

            let url = route.url_for(Some(params)).unwrap();
            assert_eq!(url, "/users/123/posts/hello-world");
        });
    }
}
