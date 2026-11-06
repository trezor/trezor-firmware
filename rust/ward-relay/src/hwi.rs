//! Forward on a caller-provided Trezor session. No device transport is opened here.

use serde_json::{json, Value};

use crate::{Client, Error};

pub type NamedMessage = (String, Value);
pub type ProofHandler<'a> = dyn FnMut(&str, Value) -> Result<Value, Error> + 'a;

/// The HWI implements protobuf encoding, device I/O, PINs and confirmations.
pub trait DeviceSession {
    fn exchange(
        &mut self,
        name: &str,
        message: Value,
        proof: &mut ProofHandler<'_>,
    ) -> Result<NamedMessage, Error>;
}

pub struct Hwi<'a, S: DeviceSession> {
    relay: &'a mut Client,
    session: &'a mut S,
}

impl<'a, S: DeviceSession> Hwi<'a, S> {
    pub fn new(relay: &'a mut Client, session: &'a mut S) -> Self {
        Self { relay, session }
    }

    /// Forward a caller's ordinary protobuf, answering WARD pulls on that same session.
    pub fn forward(&mut self, name: &str, message: Value) -> Result<NamedMessage, Error> {
        let relay = &mut self.relay;
        let mut proof = |name: &str, message: Value| {
            let step = relay.answer_ward_request(name, message)?;
            Ok(step["deviceCall"]["message"].clone())
        };
        self.session.exchange(name, message, &mut proof)
    }

    pub fn call(&mut self, method: &str, params: Value) -> Result<Value, Error> {
        let mut step = self.relay.start(method, params)?;
        loop {
            if let Some(call) = step.get("deviceCall") {
                let name = call["name"]
                    .as_str()
                    .ok_or_else(|| Error::Protocol("deviceCall has no name".into()))?;
                let response = self.forward(name, call["message"].clone());
                match response {
                    Ok((name, message)) => step = self.relay.resume(&name, message)?,
                    Err(error) => {
                        // Release wardd's conversation without closing the caller's Trezor session.
                        let _ = self
                            .relay
                            .resume("Failure", json!({"message": "HWI device call failed"}));
                        return Err(error);
                    }
                }
            } else if let Some(result) = step.get("result") {
                return Ok(result.clone());
            } else if let Some(error) = step.get("error") {
                return Err(Error::Remote {
                    code: error["code"].as_str().unwrap_or("internal").into(),
                    message: error["message"]
                        .as_str()
                        .unwrap_or("WARD operation failed")
                        .into(),
                });
            } else {
                return Err(Error::Protocol("invalid WARD adapter step".into()));
            }
        }
    }
}

/// Drive WARD on the Trezor session supplied by the caller's HWI worker.
pub fn call_on_session<S: DeviceSession>(
    session: &mut S,
    adapter: &mut Client,
    method: &str,
    params: serde_json::Value,
) -> Result<serde_json::Value, Error> {
    Hwi::new(adapter, session).call(method, params)
}

/// Forward an ordinary HWI call while servicing its nested WARD proof requests.
pub fn forward_on_session<S: DeviceSession>(
    session: &mut S,
    adapter: &mut Client,
    name: &str,
    message: serde_json::Value,
) -> Result<NamedMessage, Error> {
    Hwi::new(adapter, session).forward(name, message)
}
