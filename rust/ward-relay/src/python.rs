use pyo3::{exceptions::PyRuntimeError, prelude::*};
use serde_json::Value;

use crate::Client;

fn failure(error: impl std::fmt::Display) -> PyErr {
    PyRuntimeError::new_err(error.to_string())
}

#[pyclass(name = "Client")]
struct PythonClient {
    client: Client,
}

#[pymethods]
impl PythonClient {
    #[new]
    fn new(py: Python<'_>, url: &str, token: &str) -> PyResult<Self> {
        Ok(Self {
            client: py
                .allow_threads(|| Client::connect(url, token))
                .map_err(failure)?,
        })
    }

    fn start(&mut self, py: Python<'_>, method: &str, params_json: &str) -> PyResult<String> {
        let params: Value = serde_json::from_str(params_json).map_err(failure)?;
        Ok(py
            .allow_threads(|| self.client.start(method, params))
            .map_err(failure)?
            .to_string())
    }

    fn resume(&mut self, py: Python<'_>, name: &str, message_json: &str) -> PyResult<String> {
        let message = serde_json::from_str(message_json).map_err(failure)?;
        Ok(py
            .allow_threads(|| self.client.resume(name, message))
            .map_err(failure)?
            .to_string())
    }

    fn answer_ward_request(
        &mut self,
        py: Python<'_>,
        name: &str,
        message_json: &str,
    ) -> PyResult<String> {
        let message = serde_json::from_str(message_json).map_err(failure)?;
        Ok(py
            .allow_threads(|| self.client.answer_ward_request(name, message))
            .map_err(failure)?
            .to_string())
    }

    fn set_logging(&mut self, enabled: bool) {
        self.client.set_logging(enabled);
    }
    fn close(&mut self) {
        self.client.close();
    }
}

#[pymodule]
fn _native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<PythonClient>()
}
