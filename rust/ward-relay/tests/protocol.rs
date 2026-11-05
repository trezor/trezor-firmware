use serde_json::{json, Value};
use std::{
    net::{TcpListener, TcpStream},
    thread,
};
use tungstenite::{Message, WebSocket};
use ward_relay::{Client, Error};

fn read(socket: &mut WebSocket<TcpStream>) -> Value {
    serde_json::from_str(socket.read().unwrap().to_text().unwrap()).unwrap()
}

fn send(socket: &mut WebSocket<TcpStream>, frame: Value) {
    socket.send(Message::Text(frame.to_string())).unwrap();
}

fn server(
    script: impl FnOnce(WebSocket<TcpStream>) + Send + 'static,
) -> (String, thread::JoinHandle<()>) {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let url = format!("ws://{}", listener.local_addr().unwrap());
    let task = thread::spawn(move || {
        let mut socket = tungstenite::accept(listener.accept().unwrap().0).unwrap();
        let hello = read(&mut socket);
        assert_eq!(hello["method"], "hello");
        assert_eq!(hello["params"]["token"], "test-token");
        send(
            &mut socket,
            json!({"id": hello["id"], "result": {"version": "1.0"}}),
        );
        script(socket);
    });
    (url, task)
}

#[test]
fn hands_proof_requests_back_on_the_existing_conversation() {
    let (url, task) = server(|mut socket| {
        let request = read(&mut socket);
        assert_eq!(request["method"], "lookup");
        let id = request["id"].clone();
        send(
            &mut socket,
            json!({"id": id, "deviceCall": {"name": "WARDLookup", "message": {}}}),
        );
        let proof = read(&mut socket);
        assert_eq!(proof["method"], "answerProofRequest");
        assert_ne!(proof["id"], id);
        assert_eq!(proof["params"]["request"]["entry_key"], "abc");
        send(
            &mut socket,
            json!({"id": proof["id"], "result": {"proof": []}}),
        );
        let response = read(&mut socket);
        assert_eq!(response["id"], id);
        assert_eq!(response["deviceReply"]["name"], "WARDLookupAck");
        send(&mut socket, json!({"id": id, "result": {"valid": true}}));
    });
    let mut client = Client::connect(&url, "test-token").unwrap();
    assert_eq!(
        client.start("lookup", json!({})).unwrap()["deviceCall"]["name"],
        "WARDLookup"
    );
    assert!(matches!(client.start("sync", json!({})), Err(Error::Busy)));
    let proof = client
        .resume("WARDProofRequest", json!({"entry_key": "abc"}))
        .unwrap();
    assert_eq!(proof["deviceCall"]["name"], "WARDProofAck");
    assert_eq!(
        client.resume("WARDLookupAck", json!({})).unwrap(),
        json!({"result": {"valid": true}})
    );
    task.join().unwrap();
}

#[test]
fn answers_pulls_during_ordinary_hwi_calls() {
    let (url, task) = server(|mut socket| {
        let request = read(&mut socket);
        assert_eq!(request["method"], "answerProofRequest");
        send(
            &mut socket,
            json!({"id": request["id"], "result": {"proof": []}}),
        );
    });
    let mut client = Client::connect(&url, "test-token").unwrap();
    assert_eq!(
        client
            .answer_ward_request("WARDProofRequest", json!({}))
            .unwrap(),
        json!({"deviceCall": {"name": "WARDProofAck", "message": {"proof": []}}})
    );
    task.join().unwrap();
}

#[test]
fn refuses_non_ward_device_commands_before_the_hwi_sees_them() {
    let (url, task) = server(|mut socket| {
        let request = read(&mut socket);
        send(
            &mut socket,
            json!({"id": request["id"], "deviceCall": {"name": "GetAddress", "message": {}}}),
        );
        assert_eq!(read(&mut socket)["deviceReply"]["name"], "Failure");
    });
    let mut client = Client::connect(&url, "test-token").unwrap();
    assert!(matches!(
        client.start("sync", json!({})),
        Err(Error::Protocol(_))
    ));
    task.join().unwrap();
}

#[test]
fn returns_errors_without_fabricating_device_replies() {
    let (url, task) = server(|mut socket| {
        let request = read(&mut socket);
        send(
            &mut socket,
            json!({"id": request["id"], "error": {"code": "wm_conflict", "message": "stale"}}),
        );
    });
    let mut client = Client::connect(&url, "test-token").unwrap();
    assert!(client
        .start("sync", json!({}))
        .unwrap()
        .get("error")
        .is_some());
    assert!(matches!(
        client.resume("WARDSyncAck", json!({})),
        Err(Error::NoConversation)
    ));
    task.join().unwrap();
}
