use std::sync::{Arc, Mutex};

use napi::{bindgen_prelude::AsyncTask, Env, Error, Result, Task};
use napi_derive::napi;
use serde_json::Value;

use crate::Client;

fn failure(error: impl std::fmt::Display) -> Error {
    Error::from_reason(error.to_string())
}

#[napi]
pub struct NativeClient {
    client: Arc<Mutex<Option<Client>>>,
}

pub struct ConnectTask {
    url: String,
    token: String,
}

#[napi]
impl Task for ConnectTask {
    type Output = Client;
    type JsValue = NativeClient;

    fn compute(&mut self) -> Result<Client> {
        Client::connect(&self.url, &self.token).map_err(failure)
    }

    fn resolve(&mut self, _env: Env, client: Client) -> Result<NativeClient> {
        Ok(NativeClient {
            client: Arc::new(Mutex::new(Some(client))),
        })
    }
}

#[napi]
pub fn connect(url: String, token: String) -> AsyncTask<ConnectTask> {
    AsyncTask::new(ConnectTask { url, token })
}

enum Operation {
    Start(String, String),
    Resume(String, String),
    Proof(String, String),
    Logging(bool),
    Close,
}

pub struct StepTask {
    client: Arc<Mutex<Option<Client>>>,
    operation: Operation,
}

#[napi]
impl Task for StepTask {
    type Output = String;
    type JsValue = String;

    fn compute(&mut self) -> Result<String> {
        let mut slot = self
            .client
            .try_lock()
            .map_err(|_| failure("adapter is busy"))?;
        if matches!(self.operation, Operation::Close) {
            if let Some(mut client) = slot.take() {
                client.close();
            }
            return Ok("{}".into());
        }
        let client = slot.as_mut().ok_or_else(|| failure("adapter is closed"))?;
        let parse = |text: &str| serde_json::from_str::<Value>(text).map_err(failure);
        let result = match &self.operation {
            Operation::Start(method, params) => client.start(method, parse(params)?),
            Operation::Resume(name, message) => client.resume(name, parse(message)?),
            Operation::Proof(name, message) => client.answer_ward_request(name, parse(message)?),
            Operation::Logging(enabled) => {
                client.set_logging(*enabled);
                Ok(serde_json::json!({}))
            }
            Operation::Close => unreachable!(),
        };
        result.map(|value| value.to_string()).map_err(failure)
    }

    fn resolve(&mut self, _env: Env, output: String) -> Result<String> {
        Ok(output)
    }
}

impl NativeClient {
    fn task(&self, operation: Operation) -> AsyncTask<StepTask> {
        AsyncTask::new(StepTask {
            client: self.client.clone(),
            operation,
        })
    }
}

#[napi]
impl NativeClient {
    #[napi]
    pub fn start(&self, method: String, params_json: String) -> AsyncTask<StepTask> {
        self.task(Operation::Start(method, params_json))
    }

    #[napi]
    pub fn resume(&self, name: String, message_json: String) -> AsyncTask<StepTask> {
        self.task(Operation::Resume(name, message_json))
    }

    #[napi]
    pub fn answer_ward_request(&self, name: String, message_json: String) -> AsyncTask<StepTask> {
        self.task(Operation::Proof(name, message_json))
    }

    #[napi]
    pub fn set_logging(&self, enabled: bool) -> AsyncTask<StepTask> {
        self.task(Operation::Logging(enabled))
    }

    #[napi]
    pub fn close(&self) -> AsyncTask<StepTask> {
        self.task(Operation::Close)
    }
}
