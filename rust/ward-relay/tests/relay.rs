//! The relay client against a scripted wardd: the handshake, conversations (every deviceCall
//! answered once, in order), pipe errors carried back as Failures, wardd's codes kept.

use futures_util::{SinkExt, StreamExt};
use serde_json::{json, Value};
use std::sync::{Arc, Mutex};
use tokio::net::TcpListener;
use tokio_tungstenite::{accept_async, tungstenite::Message};
use ward_relay::{PipeError, RelayError, WardPipe, WarddClient};

type Log = Arc<Mutex<Vec<Value>>>;

/// One wardd per test; `sync` runs WardSync then WardReconcile, echoing both replies back.
async fn start_wardd() -> (String, Log) {
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let url = format!("ws://{}", listener.local_addr().unwrap());
    let log: Log = Arc::default();
    let seen = log.clone();
    tokio::spawn(async move {
        while let Ok((stream, _)) = listener.accept().await {
            let seen = seen.clone();
            tokio::spawn(async move {
                let Ok(mut ws) = accept_async(stream).await else { return };
                let recv = async |ws: &mut tokio_tungstenite::WebSocketStream<_>| loop {
                    match ws.next().await {
                        Some(Ok(Message::Text(t))) => {
                            let v: Value = serde_json::from_str(&t).unwrap();
                            seen.lock().unwrap().push(v.clone());
                            return Some(v);
                        }
                        Some(Ok(_)) => continue,
                        _ => return None,
                    }
                };
                while let Some(frame) = recv(&mut ws).await {
                    let id = frame["id"].clone();
                    let send = |v: Value| Message::Text(v.to_string());
                    match frame["method"].as_str() {
                        Some("hello") if frame["params"]["token"] == "good" => {
                            ws.send(send(json!({"id": id, "result": {"version": "1.0"}}))).await.unwrap()
                        }
                        Some("hello") => ws
                            .send(send(json!({"id": id, "error": {"code": "unauthorised", "message": "no"}})))
                            .await
                            .unwrap(),
                        Some("sync") => {
                            ws.send(Message::Ping(b"hi".to_vec())).await.unwrap();
                            ws.send(send(json!({"id": id, "deviceCall": {"name": "WardSync", "message": {}}})))
                                .await
                                .unwrap();
                            let first = recv(&mut ws).await.unwrap()["deviceReply"].clone();
                            ws.send(send(
                                json!({"id": id, "deviceCall": {"name": "WardReconcile", "message": {"x": 1}}}),
                            ))
                            .await
                            .unwrap();
                            let second = recv(&mut ws).await.unwrap()["deviceReply"].clone();
                            ws.send(send(json!({"id": id, "result": {"replies": [first, second]}})))
                                .await
                                .unwrap();
                        }
                        Some("refused") => ws
                            .send(send(json!({"id": id, "error": {"code": "needs_rejoin", "message": "fork"}})))
                            .await
                            .unwrap(),
                        Some("hangup") => return,
                        _ => ws.send(send(json!({"id": id, "result": frame["params"]}))).await.unwrap(),
                    }
                }
            });
        }
    });
    (url, log)
}

struct Scripted(Vec<String>, Option<PipeError>);

impl WardPipe for Scripted {
    async fn call(&mut self, name: &str, message: Value) -> Result<(String, Value), PipeError> {
        self.0.push(name.to_owned());
        if let Some(e) = self.1.clone() {
            return Err(e);
        }
        Ok((format!("{name}Ack"), json!({ "n": self.0.len(), "got": message })))
    }
}

#[tokio::test]
async fn hello_carries_the_token_and_a_wrong_one_is_refused() {
    let (url, log) = start_wardd().await;
    WarddClient::connect(&url, "good").await.unwrap().close().await;
    assert_eq!(
        log.lock().unwrap()[0],
        json!({"id": 1, "method": "hello", "params": {"version": "1.0", "token": "good"}})
    );
    let err = WarddClient::connect(&url, "bad").await.err().unwrap();
    assert_eq!(err.code(), Some("unauthorised"));
}

#[tokio::test]
async fn wardd_not_running_is_said_plainly() {
    let err = WarddClient::connect("ws://127.0.0.1:1", "good").await.err().unwrap();
    assert!(matches!(err, RelayError::Unreachable { .. }), "{err}");
}

#[tokio::test]
async fn a_conversation_answers_each_device_call_in_order() {
    let (url, _) = start_wardd().await;
    let mut client = WarddClient::connect(&url, "good").await.unwrap();
    let mut pipe = Scripted(vec![], None);
    let out = client.sync(&mut pipe, false).await.unwrap();
    assert_eq!(pipe.0, ["WardSync", "WardReconcile"]);
    assert_eq!(
        out,
        json!({"replies": [
            {"name": "WardSyncAck", "message": {"n": 1, "got": {}}},
            {"name": "WardReconcileAck", "message": {"n": 2, "got": {"x": 1}}},
        ]})
    );
}

#[tokio::test]
async fn a_device_failure_and_a_broken_pipe_both_go_back_as_failures() {
    let (url, _) = start_wardd().await;
    let mut client = WarddClient::connect(&url, "good").await.unwrap();
    let failure =
        PipeError::Failure { code: Some("Failure_DataError".into()), message: "no".into() };
    let out = client.sync(&mut Scripted(vec![], Some(failure)), false).await.unwrap();
    assert_eq!(
        out["replies"][0],
        json!({"name": "Failure", "message": {"code": "Failure_DataError", "message": "no"}})
    );
    let out = client
        .sync(&mut Scripted(vec![], Some(PipeError::Other("gone".into()))), false)
        .await
        .unwrap();
    assert_eq!(out["replies"][1], json!({"name": "Failure", "message": {"message": "gone"}}));
}

#[tokio::test]
async fn wardds_codes_are_kept_and_a_hangup_is_an_error() {
    let (url, _) = start_wardd().await;
    let mut client = WarddClient::connect(&url, "good").await.unwrap();
    let err = client.call_without_device("refused", json!({})).await.err().unwrap();
    assert_eq!(err.code(), Some("needs_rejoin"));
    let err = client.call_without_device("hangup", json!({})).await.err().unwrap();
    assert!(matches!(err, RelayError::Connection(_)), "{err}");
}

#[tokio::test]
async fn the_thin_calls_send_the_contracts_params() {
    let (url, log) = start_wardd().await;
    let mut client = WarddClient::connect(&url, "good").await.unwrap();
    client.open_store(&mut Scripted(vec![], None), Some(&[0xab; 32]), Some(&[1, 2])).await.unwrap();
    client.serve_entry(json!({"entry_key": "aa"}), &[(vec![1], vec![2])]).await.unwrap();
    let log = log.lock().unwrap();
    assert_eq!(log[1]["params"], json!({"wardId": "ab".repeat(32), "evoluNode": "0102"}));
    assert_eq!(log[2]["params"], json!({"request": {"entry_key": "aa"}, "staged": [["01", "02"]]}));
}

/// With `WARDD_SUITE_DIR` set: the real wardd, which this client must reach with no Origin header.
#[tokio::test]
async fn against_real_wardd() {
    let Ok(suite) = std::env::var("WARDD_SUITE_DIR") else { return };
    let dir = std::env::temp_dir().join(format!("ward-relay-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    std::fs::write(dir.join("token"), "rust-test").unwrap();
    let port = std::net::TcpListener::bind("127.0.0.1:0").unwrap().local_addr().unwrap().port();
    // `node --import tsx`, not the tsx binary: that one spawns a child node, and killing it would
    // orphan the daemon (holding the test runner's output pipe open)
    let mut wardd = std::process::Command::new("node")
        .args(["--import", "tsx", "packages/wardd/src/cli.ts", "--memory"])
        .args(["--port", &port.to_string()])
        .args([
            "--data-dir",
            dir.to_str().unwrap(),
            "--token-file",
            dir.join("token").to_str().unwrap(),
        ])
        .current_dir(&suite)
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .spawn()
        .unwrap();
    let url = format!("ws://127.0.0.1:{port}");
    let mut client = None;
    for _ in 0..100 {
        if let Ok(c) = WarddClient::connect(&url, "rust-test").await {
            client = Some(c);
            break;
        }
        tokio::time::sleep(std::time::Duration::from_millis(100)).await;
    }
    let mut client = client.expect("wardd started");
    let opened =
        client.open_store(&mut Scripted(vec![], None), Some(&[7; 32]), None).await.unwrap();
    assert_eq!(opened, json!({"counter": 0, "root": null}));
    let status = client.status().await.unwrap();
    assert_eq!(status["wmCounter"], Value::Null);
    let err = WarddClient::connect(&url, "wrong").await.err().unwrap();
    assert_eq!(err.code(), Some("unauthorised"));
    client.close().await;
    wardd.kill().unwrap();
    wardd.wait().unwrap();
}
