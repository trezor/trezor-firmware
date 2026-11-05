//! WARD relay steps for an HWI-owned device session. This crate opens only the
//! wardd WebSocket. The caller encodes, sends and receives every device protobuf.

use std::{net::TcpStream, time::Instant};

use chrono::{SecondsFormat, Utc};
use serde_json::{json, Value};
use tungstenite::{stream::MaybeTlsStream, Message, WebSocket};

#[cfg(feature = "python")]
mod python;

pub const DEFAULT_URL: &str = "ws://127.0.0.1:21329";
const DEVICE_CALLS: &[&str] = &[
    "WARDSync",
    "WARDIngestAttestation",
    "WARDReconcile",
    "WARDLookup",
    "WARDQueueUpdate",
    "WARDPerformUpdate",
    "WARDConfirmedByWM",
    "WARDDiscardPending",
];

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("wardd connection: {0}")]
    Connection(String),
    #[error("wardd protocol: {0}")]
    Protocol(String),
    #[error("{code}: {message}")]
    Remote { code: String, message: String },
    #[error("a WARD conversation is already active")]
    Busy,
    #[error("no WARD conversation is awaiting a device reply")]
    NoConversation,
}

/// A blocking step engine. Run on the HWI's transport worker, never its UI thread.
pub struct Client {
    socket: WebSocket<MaybeTlsStream<TcpStream>>,
    next_id: u64,
    pending: Option<(u64, Instant)>,
    logging: bool,
}

impl Client {
    pub fn connect(url: &str, token: &str) -> Result<Self, Error> {
        let config = tungstenite::protocol::WebSocketConfig {
            max_message_size: Some(16 << 20),
            max_frame_size: Some(16 << 20),
            ..Default::default()
        };
        let (socket, _) = tungstenite::client::connect_with_config(url, Some(config), 0)
            .map_err(|error| Error::Connection(error.to_string()))?;
        let mut client = Self {
            socket,
            next_id: 1,
            pending: None,
            logging: true,
        };
        if let MaybeTlsStream::Plain(stream) = client.socket.get_mut() {
            let timeout = Some(std::time::Duration::from_secs(60));
            stream
                .set_read_timeout(timeout)
                .map_err(|error| Error::Connection(error.to_string()))?;
            stream
                .set_write_timeout(timeout)
                .map_err(|error| Error::Connection(error.to_string()))?;
        }
        let hello = client.rpc("hello", json!({"version": "1.0", "token": token}))?;
        if hello
            .get("version")
            .and_then(Value::as_str)
            .and_then(|version| version.split('.').next())
            != Some("1")
        {
            return Err(Error::Protocol("incompatible relay version".into()));
        }
        Ok(client)
    }

    pub fn set_logging(&mut self, enabled: bool) {
        self.logging = enabled;
    }

    fn log(&self, event: &str, id: u64, details: Value) {
        if self.logging {
            eprintln!(
                "{}",
                json!({
                    "time": Utc::now().to_rfc3339_opts(SecondsFormat::Millis, true),
                    "service": "ward-adapter", "event": event, "id": id, "details": details,
                })
            );
        }
    }

    /// Begin `sync`, `lookup`, `update` or `status`. Returns a `deviceCall` step
    /// for the existing HWI session, or a final `result`/`error` step.
    pub fn start(&mut self, method: &str, params: Value) -> Result<Value, Error> {
        if self.pending.is_some() {
            return Err(Error::Busy);
        }
        if !["sync", "lookup", "update", "status"].contains(&method) {
            return Err(Error::Protocol("unsupported WARD method".into()));
        }
        let id = self.next_id;
        self.next_id += 1;
        self.log("request", id, json!({"method": method}));
        self.send(json!({"id": id, "method": method, "params": params}))?;
        self.pending = Some((id, Instant::now()));
        self.next_step()
    }

    /// Hand the device's named protobuf response back to wardd. A mid-call
    /// WARDProofRequest is answered without ending the original conversation.
    pub fn resume(&mut self, name: &str, message: Value) -> Result<Value, Error> {
        let id = self.pending.as_ref().ok_or(Error::NoConversation)?.0;
        self.log("device_response", id, json!({"name": name}));
        if name == "WARDProofRequest" {
            return self.answer_ward_request(name, message);
        }
        self.send(json!({"id": id, "deviceReply": {"name": name, "message": message}}))?;
        self.next_step()
    }

    /// Answer a WARD pull received during an ordinary HWI call (for example
    /// address display). The HWI sends the returned WARDProofAck on its channel.
    pub fn answer_ward_request(&mut self, name: &str, message: Value) -> Result<Value, Error> {
        if name != "WARDProofRequest" {
            return Err(Error::Protocol(
                "only WARDProofRequest can be answered".into(),
            ));
        }
        let ack = self.rpc("answerProofRequest", json!({"request": message}))?;
        Ok(json!({"deviceCall": {"name": "WARDProofAck", "message": ack}}))
    }

    fn next_step(&mut self) -> Result<Value, Error> {
        let id = self.pending.as_ref().ok_or(Error::NoConversation)?.0;
        let frame = match self.receive(id) {
            Ok(frame) => frame,
            Err(error) => {
                self.pending = None;
                return Err(error);
            }
        };
        if let Some(call) = frame.get("deviceCall") {
            let name = call.get("name").and_then(Value::as_str).unwrap_or("");
            if !DEVICE_CALLS.contains(&name) {
                self.log(
                    "rejected_device_call",
                    id,
                    json!({"reason": "not_a_ward_message"}),
                );
                self.send(json!({"id": id, "deviceReply": {"name": "Failure", "message": {"message": "wardd may only send WARD messages"}}}))?;
                self.close();
                return Err(Error::Protocol(
                    "wardd attempted a non-WARD device call".into(),
                ));
            }
            self.log("device_request", id, json!({"name": name}));
            return Ok(json!({"deviceCall": call}));
        }
        let elapsed = self
            .pending
            .take()
            .ok_or(Error::NoConversation)?
            .1
            .elapsed()
            .as_millis();
        if let Some(error) = frame.get("error") {
            self.log(
                "response",
                id,
                json!({"outcome": "error", "durationMs": elapsed}),
            );
            return Ok(json!({"error": error}));
        }
        if let Some(result) = frame.get("result") {
            self.log(
                "response",
                id,
                json!({"outcome": "ok", "durationMs": elapsed}),
            );
            return Ok(json!({"result": result}));
        }
        Err(Error::Protocol(
            "expected deviceCall, result or error".into(),
        ))
    }

    fn rpc(&mut self, method: &str, params: Value) -> Result<Value, Error> {
        let id = self.next_id;
        self.next_id += 1;
        let started = Instant::now();
        self.log("request", id, json!({"method": method}));
        let result = (|| {
            self.send(json!({"id": id, "method": method, "params": params}))?;
            let frame = self.receive(id)?;
            if let Some(error) = frame.get("error") {
                return Err(Error::Remote {
                    code: error
                        .get("code")
                        .and_then(Value::as_str)
                        .unwrap_or("internal")
                        .into(),
                    message: error
                        .get("message")
                        .and_then(Value::as_str)
                        .unwrap_or("")
                        .into(),
                });
            }
            frame
                .get("result")
                .cloned()
                .ok_or_else(|| Error::Protocol("expected a result".into()))
        })();
        self.log("response", id, json!({"outcome": if result.is_ok() { "ok" } else { "error" }, "durationMs": started.elapsed().as_millis()}));
        result
    }

    fn send(&mut self, value: Value) -> Result<(), Error> {
        self.socket
            .send(Message::Text(value.to_string()))
            .map_err(|error| Error::Connection(error.to_string()))
    }

    fn receive(&mut self, id: u64) -> Result<Value, Error> {
        loop {
            match self
                .socket
                .read()
                .map_err(|error| Error::Connection(error.to_string()))?
            {
                Message::Text(text) => {
                    let frame: Value = serde_json::from_str(&text)
                        .map_err(|error| Error::Protocol(error.to_string()))?;
                    if frame.get("id").and_then(Value::as_u64) != Some(id) {
                        return Err(Error::Protocol("unexpected response id".into()));
                    }
                    return Ok(frame);
                }
                Message::Ping(_) => self
                    .socket
                    .flush()
                    .map_err(|error| Error::Connection(error.to_string()))?,
                Message::Pong(_) => {}
                _ => return Err(Error::Protocol("expected a text frame".into())),
            }
        }
    }

    pub fn close(&mut self) {
        let _ = self.socket.close(None);
        self.pending = None;
    }
}

impl Drop for Client {
    fn drop(&mut self) {
        self.close();
    }
}
