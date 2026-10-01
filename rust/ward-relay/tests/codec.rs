//! Messages by name from the firmware's own protos, codec-v1 chunking, and the pipe's handling of
//! what the user is part of.
#![cfg(feature = "codec")]

use serde_json::{json, Value};
use std::{collections::VecDeque, io};
use ward_relay::{
    codec::{chunks, decode, encode, type_id, type_name, CodecPipe, FrameIo, Reassembly},
    PipeError, WardPipe,
};

#[test]
fn names_map_to_the_firmwares_wire_ids() {
    assert_eq!(type_id("WardSync"), Some(2307));
    assert_eq!(type_id("WardChainRequest"), Some(2345));
    assert_eq!(type_id("WardRejoin"), Some(2347));
    assert_eq!(type_name(2347).as_deref(), Some("WardRejoin"));
    assert_eq!(type_id("NotAMessage"), None);
}

#[test]
fn a_batched_ack_round_trips_with_bytes_as_hex() {
    let body = json!({
        "counter": 7,
        "auth_commit": "11".repeat(32),
        "wm_sig": "22".repeat(64),
        "remaining": 0,
        "from_counter": 4,
        "leaves": [
            {"entry_key": "33".repeat(32), "content": {"encoding": 1, "plaintext": {"content": "aabb"}}},
            {"entry_key": "44".repeat(32)},
        ],
    });
    let (id, bytes) = encode("WardFlushQueueAck", &body).unwrap();
    let (name, back) = decode(id, &bytes).unwrap();
    assert_eq!(name, "WardFlushQueueAck");
    assert_eq!(back, body);
}

#[test]
fn enums_travel_by_name_and_bad_input_is_refused() {
    let (id, bytes) =
        encode("Failure", &json!({"code": "Failure_DataError", "message": "x"})).unwrap();
    assert_eq!(decode(id, &bytes).unwrap().1, json!({"code": "Failure_DataError", "message": "x"}));
    assert!(encode("WardSync", &json!({"nope": 1})).unwrap_err().contains("no field nope"));
    assert!(encode("WardEntryAck", &json!({"proof": ["zz"]})).is_err());
    assert!(encode("NotAMessage", &json!({})).unwrap_err().contains("unknown message"));
}

#[test]
fn chunking_reassembles_a_message_spanning_several_packets() {
    let payload: Vec<u8> = (0..200u8).collect();
    let packets = chunks(2307, &payload);
    assert!(packets.len() > 3 && packets.iter().all(|c| c[0] == b'?'));
    assert_eq!(&packets[0][..3], b"?##");
    let mut r = Reassembly::default();
    let mut out = None;
    for p in &packets {
        out = r.push(p).unwrap();
    }
    assert_eq!(out, Some((2307, payload)));
    assert!(Reassembly::default().push(b"xx").is_err());
}

/// Replays a script of device replies; records what was written.
struct ScriptedIo {
    replies: VecDeque<(&'static str, Value)>,
    written: Vec<String>,
}

impl FrameIo for ScriptedIo {
    fn write(&mut self, id: u16, payload: &[u8]) -> io::Result<()> {
        self.written.push(decode(id, payload).unwrap().0);
        Ok(())
    }
    fn read(&mut self) -> io::Result<(u16, Vec<u8>)> {
        let (name, body) = self.replies.pop_front().expect("a scripted reply");
        Ok(encode(name, &body).unwrap())
    }
}

fn pipe(replies: Vec<(&'static str, Value)>) -> CodecPipe<ScriptedIo> {
    CodecPipe::new(ScriptedIo { replies: replies.into(), written: vec![] })
}

#[tokio::test]
async fn buttons_are_acked_and_pulls_are_returned() {
    let mut p = pipe(vec![
        ("ButtonRequest", json!({})),
        ("WardEntryRequest", json!({"entry_key": "55".repeat(32)})),
    ]);
    let (name, body) = p.call("WardFlushQueue", json!({"max_batch": 2})).await.unwrap();
    assert_eq!((name.as_str(), body), ("WardEntryRequest", json!({"entry_key": "55".repeat(32)})));
    assert_eq!(p.into_inner().written, ["WardFlushQueue", "ButtonAck"]);
}

#[tokio::test]
async fn a_failure_is_the_devices_and_a_passphrase_is_never_guessed() {
    let mut p = pipe(vec![(
        "Failure",
        json!({"code": "Failure_DataError", "message": "does not descend"}),
    )]);
    assert_eq!(
        p.call("WardVerifyChain", json!({})).await.unwrap_err(),
        PipeError::Failure {
            code: Some("Failure_DataError".into()),
            message: "does not descend".into()
        }
    );
    let mut p = pipe(vec![("PassphraseRequest", json!({}))]);
    assert!(matches!(p.call("WardSync", json!({})).await.unwrap_err(), PipeError::Other(_)));
    let mut p =
        pipe(vec![("PassphraseRequest", json!({})), ("WardSyncAck", json!({"counter": 0}))]);
    p.passphrase = Some(String::new());
    assert_eq!(p.call("WardSync", json!({})).await.unwrap().0, "WardSyncAck");
}
