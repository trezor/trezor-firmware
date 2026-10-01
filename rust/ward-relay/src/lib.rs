//! The Rust binding of the **wardd relay** -- for BHWI, async-hwi and any other Rust host that
//! talks to a Trezor.
//!
//! `wardd` is the local WARD service: it holds the wallet's replica (in Evolu), the WM client, and
//! the order of every sync, catch-up and flush. A binding carries messages between it and the
//! device on the session the host already holds, and nothing more -- the same contract the
//! Connect, Python and Java bindings implement (`packages/ward-core/relay.md` in trezor-suite,
//! version 1.x):
//!
//! ```text
//! client -> wardd   {id, method, params}
//! wardd  -> client  {id, deviceCall: {name, message}}    send this to the device
//! client -> wardd   {id, deviceReply: {name, message}}   what the device said, pulls included
//! wardd  -> client  {id, result} | {id, error: {code, message}}
//! ```
//!
//! Messages travel BY NAME with a JSON body, bytes as lowercase hex. A host implements
//! [`WardPipe`] on its own transport -- put this named message on the device, return what came
//! back -- and the conversation loop in [`WarddClient::call`] does the rest. The `codec` feature
//! supplies such a pipe for codec-v1 framing, encoding from the firmware's own `.proto` files.

#[cfg(feature = "codec")]
pub mod codec;

use futures_util::{SinkExt, StreamExt};
use serde_json::{json, Value};
use tokio::net::TcpStream;
use tokio_tungstenite::{
    tungstenite::{client::IntoClientRequest, Message},
    MaybeTlsStream, WebSocketStream,
};

pub const WARDD_DEFAULT_URL: &str = "ws://127.0.0.1:21329";
pub const RELAY_PROTOCOL_VERSION: &str = "1.0";

#[derive(Debug, thiserror::Error)]
pub enum RelayError {
    /// wardd's refusal; `code` is the contract's (`wm_conflict`, `needs_rejoin`, ...).
    #[error("{code}: {message}")]
    Wardd { code: String, message: String },
    #[error("wardd is not reachable at {url}: {reason}")]
    Unreachable { url: String, reason: String },
    #[error("wardd connection: {0}")]
    Connection(String),
    #[error("wardd protocol: {0}")]
    Protocol(String),
}

impl RelayError {
    /// The contract's error code, when wardd refused.
    pub fn code(&self) -> Option<&str> {
        match self {
            RelayError::Wardd { code, .. } => Some(code),
            _ => None,
        }
    }
}

/// Why a pipe could not produce the device's reply.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PipeError {
    /// The device answered `Failure`: part of the conversation, and reported to wardd as such.
    Failure { code: Option<String>, message: String },
    /// The pipe itself broke (transport, encoding). Still reported to wardd as a Failure, so the
    /// conversation ends and the wallet is released rather than waited on.
    Other(String),
}

/// The frame pipe: put one named message on the device and hand back what it said.
///
/// RETURN PULLS AS-IS. `WardEntryRequest` and `WardChainRequest` are wardd's conversation; a pipe
/// that answered them itself would be answering wardd's question behind its back. Handle only
/// what the user is part of -- button requests, PIN, passphrase -- the way the host always does.
#[allow(async_fn_in_trait)]
pub trait WardPipe {
    async fn call(&mut self, name: &str, message: Value) -> Result<(String, Value), PipeError>;
}

/// For calls that need no device (`status`, `serveEntry`, ...).
pub struct NoDevice;

impl WardPipe for NoDevice {
    async fn call(&mut self, name: &str, _: Value) -> Result<(String, Value), PipeError> {
        Err(PipeError::Other(format!("no device to answer {name}")))
    }
}

/// One authenticated socket to wardd. Calls are sequential, as a device session's calls are.
pub struct WarddClient {
    ws: WebSocketStream<MaybeTlsStream<TcpStream>>,
    next_id: u64,
}

impl WarddClient {
    /// Open the socket and say hello with the pairing token.
    ///
    /// NO Origin header is sent: only a browser sends one, and wardd checks it against its
    /// allow-list; a local process is admitted on the token alone.
    pub async fn connect(url: &str, token: &str) -> Result<Self, RelayError> {
        let request = url
            .into_client_request()
            .map_err(|e| RelayError::Unreachable { url: url.into(), reason: e.to_string() })?;
        let (ws, _) = tokio_tungstenite::connect_async(request)
            .await
            .map_err(|e| RelayError::Unreachable { url: url.into(), reason: e.to_string() })?;
        let mut client = WarddClient { ws, next_id: 1 };
        if let Err(e) = client
            .call_without_device(
                "hello",
                json!({ "version": RELAY_PROTOCOL_VERSION, "token": token }),
            )
            .await
        {
            client.close().await;
            return Err(e);
        }
        Ok(client)
    }

    /// One call; a CONVERSATION when wardd needs the device, answered through `pipe`.
    ///
    /// EVERY deviceCall GETS A deviceReply: a pipe error goes back as a `Failure`, so wardd ends
    /// the conversation -- and releases the wallet -- instead of waiting for a reply.
    pub async fn call<P: WardPipe>(
        &mut self,
        method: &str,
        params: Value,
        mut pipe: Option<&mut P>,
    ) -> Result<Value, RelayError> {
        let id = self.next_id;
        self.next_id += 1;
        self.send(json!({ "id": id, "method": method, "params": params })).await?;
        loop {
            let frame = self.recv().await?;
            if frame.get("id").and_then(Value::as_u64) != Some(id) {
                continue;
            }
            if let Some(call) = frame.get("deviceCall") {
                let name = call.get("name").and_then(Value::as_str).unwrap_or_default().to_owned();
                let message = call.get("message").cloned().unwrap_or_else(|| json!({}));
                let outcome = match pipe.as_deref_mut() {
                    Some(p) => p.call(&name, message).await,
                    None => Err(PipeError::Other(format!("no device to answer {name}"))),
                };
                let reply = match outcome {
                    Ok((name, message)) => json!({ "name": name, "message": message }),
                    Err(PipeError::Failure { code, message }) => {
                        json!({ "name": "Failure", "message": { "code": code, "message": message } })
                    }
                    Err(PipeError::Other(message)) => {
                        json!({ "name": "Failure", "message": { "message": message } })
                    }
                };
                self.send(json!({ "id": id, "deviceReply": reply })).await?;
                continue;
            }
            if let Some(error) = frame.get("error") {
                return Err(RelayError::Wardd {
                    code: error.get("code").and_then(Value::as_str).unwrap_or("internal").into(),
                    message: error
                        .get("message")
                        .and_then(Value::as_str)
                        .unwrap_or_default()
                        .into(),
                });
            }
            return frame.get("result").cloned().ok_or_else(|| {
                RelayError::Protocol("a frame with neither result nor error".into())
            });
        }
    }

    pub async fn call_without_device(
        &mut self,
        method: &str,
        params: Value,
    ) -> Result<Value, RelayError> {
        self.call::<NoDevice>(method, params, None).await
    }

    /// Select the wallet: by `ward_id`, or the device's own (asked with `WardSync`). `evolu_node`
    /// is the 64-byte node the device returns for `EvoluGetNode`; wardd derives the replica's
    /// owner from its child `WARD`. A wardd started with `--memory` needs none.
    pub async fn open_store<P: WardPipe>(
        &mut self,
        pipe: &mut P,
        ward_id: Option<&[u8]>,
        evolu_node: Option<&[u8]>,
    ) -> Result<Value, RelayError> {
        let ward_id = match ward_id {
            Some(id) => hex_of(id),
            None => {
                let (name, ack) = pipe
                    .call("WardSync", json!({}))
                    .await
                    .map_err(|e| RelayError::Protocol(format!("WardSync: {e:?}")))?;
                if name != "WardSyncAck" {
                    return Err(RelayError::Protocol(format!("WardSync answered {name}")));
                }
                ack.get("ward_id")
                    .and_then(Value::as_str)
                    .ok_or_else(|| RelayError::Protocol("the device reported no ward_id".into()))?
                    .to_owned()
            }
        };
        let mut params = json!({ "wardId": ward_id });
        if let Some(node) = evolu_node {
            params["evoluNode"] = json!(hex_of(node));
        }
        self.call_without_device("openStore", params).await
    }

    /// Bring the device to the WM's head. `rejoin` recovers a device on a fork, discarding its
    /// changes above it -- confirmed on the device; without it wardd answers `needs_rejoin`.
    pub async fn sync<P: WardPipe>(
        &mut self,
        pipe: &mut P,
        rejoin: bool,
    ) -> Result<Value, RelayError> {
        self.call("sync", json!({ "rejoin": rejoin }), Some(pipe)).await
    }

    /// Publish everything the device holds queued, syncing after each transition; `max_batch`
    /// folds up to that many changes into one. One session for the whole drain.
    pub async fn flush<P: WardPipe>(
        &mut self,
        pipe: &mut P,
        max_batch: u32,
    ) -> Result<Value, RelayError> {
        self.call("flush", json!({ "maxBatch": max_batch }), Some(pipe)).await
    }

    /// The replica's head and the WM's, for the store last opened.
    pub async fn status(&mut self) -> Result<Value, RelayError> {
        self.call_without_device("status", json!({})).await
    }

    /// Answer one pull from wardd's replica, for a host that drives a pulling call itself.
    /// `staged` is CUMULATIVE for a batched flush: every (entry_key, commit) folded so far.
    pub async fn serve_entry(
        &mut self,
        request: Value,
        staged: &[(Vec<u8>, Vec<u8>)],
    ) -> Result<Value, RelayError> {
        let staged: Vec<Value> =
            staged.iter().map(|(k, c)| json!([hex_of(k), hex_of(c)])).collect();
        self.call_without_device("serveEntry", json!({ "request": request, "staged": staged }))
            .await
    }

    /// Store and publish what a write handed back (a `WardLeafAck` / `WardFlushQueueAck` body).
    pub async fn apply_result(&mut self, result: Value) -> Result<Value, RelayError> {
        self.call_without_device("applyResult", result).await
    }

    pub async fn close(mut self) {
        let _ = self.ws.close(None).await;
    }

    async fn send(&mut self, frame: Value) -> Result<(), RelayError> {
        self.ws
            .send(Message::Text(frame.to_string()))
            .await
            .map_err(|e| RelayError::Connection(e.to_string()))
    }

    async fn recv(&mut self) -> Result<Value, RelayError> {
        loop {
            match self.ws.next().await {
                Some(Ok(Message::Text(text))) => {
                    return serde_json::from_str(&text)
                        .map_err(|e| RelayError::Protocol(e.to_string()))
                }
                // pings are answered by tungstenite on the next write; nothing else is ours
                Some(Ok(
                    Message::Ping(_) | Message::Pong(_) | Message::Binary(_) | Message::Frame(_),
                )) => {}
                Some(Ok(Message::Close(_))) | None => {
                    return Err(RelayError::Connection("wardd closed the connection".into()))
                }
                Some(Err(e)) => return Err(RelayError::Connection(e.to_string())),
            }
        }
    }
}

fn hex_of(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}
