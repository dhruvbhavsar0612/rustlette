//! Rustlette - High-performance Python web framework with Rust internals
//!
//! This crate provides the Rust implementation of core web framework components
//! that are exposed to Python through PyO3 bindings.

use pyo3::prelude::*;

/// A minimal test function to verify PyO3 setup
#[pyfunction]
fn hello_rustlette() -> PyResult<String> {
    Ok("Hello from Rustlette!".to_string())
}

/// Simple test class to verify PyO3 class binding
#[pyclass]
struct TestApp {
    name: String,
}

#[pymethods]
impl TestApp {
    #[new]
    fn new(name: String) -> Self {
        TestApp { name }
    }

    fn get_name(&self) -> String {
        self.name.clone()
    }
}

/// Python module definition
#[pymodule]
fn _rustlette_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(hello_rustlette, m)?)?;
    m.add_class::<TestApp>()?;
    Ok(())
}
