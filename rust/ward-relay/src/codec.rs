//! A [`WardPipe`] for codec-v1 framing, encoding messages BY NAME from the firmware's own
//! `.proto` files (embedded at build time -- see `build.rs`).
//!
//! JSON follows the relay's rules: bytes are lowercase hex, enums by name, absent fields omitted.
//! The same shape `trezorlib.protobuf.to_dict` and Connect's codec produce.
//!
//! THE FRAME IO IS BLOCKING. A host with an async transport implements [`WardPipe`] directly on
//! it and does not need this module's IO; what it may still want is [`encode`] / [`decode`].
//!
//! Codec v1 only: a THP device (T3W1) needs the host's THP channel, which this crate does not
//! implement -- its pipe is the host's to write, on that channel.

use std::{io, net::UdpSocket, sync::OnceLock, time::Duration};

use protobuf::{
    descriptor::FileDescriptorSet,
    reflect::{
        EnumDescriptor, FileDescriptor, MessageDescriptor, ReflectFieldRef, ReflectValueBox,
        ReflectValueRef, RuntimeFieldType, RuntimeType,
    },
    Message, MessageDyn,
};
use serde_json::{json, Map, Value};

use crate::{PipeError, WardPipe};

struct Protos {
    files: Vec<FileDescriptor>,
    message_type: EnumDescriptor,
}

fn protos() -> &'static Protos {
    static PROTOS: OnceLock<Protos> = OnceLock::new();
    PROTOS.get_or_init(|| {
        let set = FileDescriptorSet::parse_from_bytes(include_bytes!(concat!(
            env!("OUT_DIR"),
            "/protob.bin"
        )))
        .expect("embedded descriptors");
        let files = FileDescriptor::new_dynamic_fds(set.file, &[]).expect("descriptors link");
        let message_type = files
            .iter()
            .find_map(|f| f.enum_by_package_relative_name("MessageType"))
            .expect("MessageType enum");
        Protos { files, message_type }
    })
}

fn descriptor(name: &str) -> Option<MessageDescriptor> {
    protos().files.iter().find_map(|f| f.message_by_package_relative_name(name))
}

/// The wire type id for a message name.
pub fn type_id(name: &str) -> Option<u16> {
    let value = protos().message_type.value_by_name(&format!("MessageType_{name}"))?;
    u16::try_from(value.value()).ok()
}

/// The message name for a wire type id.
pub fn type_name(id: u16) -> Option<String> {
    let value = protos().message_type.value_by_number(i32::from(id))?;
    value.name().strip_prefix("MessageType_").map(str::to_owned)
}

/// A named message's JSON body -> (wire type id, encoded bytes).
pub fn encode(name: &str, body: &Value) -> Result<(u16, Vec<u8>), String> {
    let desc = descriptor(name).ok_or_else(|| format!("unknown message {name}"))?;
    let id = type_id(name).ok_or_else(|| format!("{name} has no wire type"))?;
    let message = from_json(&desc, body)?;
    let bytes = message.write_to_bytes_dyn().map_err(|e| format!("{name}: {e}"))?;
    Ok((id, bytes))
}

/// (wire type id, bytes) -> the message's name and JSON body.
pub fn decode(id: u16, bytes: &[u8]) -> Result<(String, Value), String> {
    let name = type_name(id).ok_or_else(|| format!("unknown wire type {id}"))?;
    let desc = descriptor(&name).ok_or_else(|| format!("no descriptor for {name}"))?;
    let message = desc.parse_from_bytes(bytes).map_err(|e| format!("{name}: {e}"))?;
    Ok((name, to_json(&*message)))
}

fn from_json(desc: &MessageDescriptor, body: &Value) -> Result<Box<dyn MessageDyn>, String> {
    let mut message = desc.new_instance();
    let Some(obj) = body.as_object() else {
        return Err(format!("{} must be a JSON object", desc.name()));
    };
    for (key, value) in obj {
        if value.is_null() {
            continue;
        }
        let field =
            desc.field_by_name(key).ok_or_else(|| format!("{} has no field {key}", desc.name()))?;
        match field.runtime_field_type() {
            RuntimeFieldType::Singular(t) => {
                field.set_singular_field(&mut *message, value_box(&t, value, key)?);
            }
            RuntimeFieldType::Repeated(t) => {
                let items = value.as_array().ok_or_else(|| format!("{key} must be a list"))?;
                let mut repeated = field.mut_repeated(&mut *message);
                for item in items {
                    repeated.push(value_box(&t, item, key)?);
                }
            }
            RuntimeFieldType::Map(..) => return Err(format!("{key}: map fields are not supported")),
        }
    }
    Ok(message)
}

fn value_box(t: &RuntimeType, v: &Value, key: &str) -> Result<ReflectValueBox, String> {
    let bad = || format!("{key}: unexpected value {v}");
    Ok(match t {
        RuntimeType::U32 => {
            ReflectValueBox::U32(v.as_u64().and_then(|n| n.try_into().ok()).ok_or_else(bad)?)
        }
        RuntimeType::U64 => ReflectValueBox::U64(v.as_u64().ok_or_else(bad)?),
        RuntimeType::I32 => {
            ReflectValueBox::I32(v.as_i64().and_then(|n| n.try_into().ok()).ok_or_else(bad)?)
        }
        RuntimeType::I64 => ReflectValueBox::I64(v.as_i64().ok_or_else(bad)?),
        RuntimeType::F32 => ReflectValueBox::F32(v.as_f64().ok_or_else(bad)? as f32),
        RuntimeType::F64 => ReflectValueBox::F64(v.as_f64().ok_or_else(bad)?),
        RuntimeType::Bool => ReflectValueBox::Bool(v.as_bool().ok_or_else(bad)?),
        RuntimeType::String => ReflectValueBox::String(v.as_str().ok_or_else(bad)?.to_owned()),
        RuntimeType::VecU8 => {
            ReflectValueBox::Bytes(hex::decode(v.as_str().ok_or_else(bad)?).map_err(|_| bad())?)
        }
        RuntimeType::Enum(e) => {
            let number = match v {
                Value::String(s) => e.value_by_name(s).map(|ev| ev.value()).ok_or_else(bad)?,
                _ => v.as_i64().and_then(|n| n.try_into().ok()).ok_or_else(bad)?,
            };
            ReflectValueBox::Enum(e.clone(), number)
        }
        RuntimeType::Message(d) => ReflectValueBox::Message(from_json(d, v)?),
    })
}

fn to_json(message: &dyn MessageDyn) -> Value {
    let mut out = Map::new();
    for field in message.descriptor_dyn().fields() {
        match field.get_reflect(message) {
            ReflectFieldRef::Optional(opt) => {
                if let Some(v) = opt.value() {
                    out.insert(field.name().to_owned(), value_json(v));
                }
            }
            ReflectFieldRef::Repeated(r) => {
                if !r.is_empty() {
                    out.insert(
                        field.name().to_owned(),
                        Value::Array(r.into_iter().map(value_json).collect()),
                    );
                }
            }
            ReflectFieldRef::Map(_) => {}
        }
    }
    Value::Object(out)
}

fn value_json(v: ReflectValueRef) -> Value {
    match v {
        ReflectValueRef::U32(n) => json!(n),
        ReflectValueRef::U64(n) => json!(n),
        ReflectValueRef::I32(n) => json!(n),
        ReflectValueRef::I64(n) => json!(n),
        ReflectValueRef::F32(n) => json!(n),
        ReflectValueRef::F64(n) => json!(n),
        ReflectValueRef::Bool(b) => json!(b),
        ReflectValueRef::String(s) => json!(s),
        ReflectValueRef::Bytes(b) => json!(hex::encode(b)),
        ReflectValueRef::Enum(e, n) => e.value_by_number(n).map_or(json!(n), |ev| json!(ev.name())),
        ReflectValueRef::Message(m) => to_json(&*m),
    }
}

/// Moves whole messages: (wire type id, payload).
pub trait FrameIo {
    fn write(&mut self, id: u16, payload: &[u8]) -> io::Result<()>;
    fn read(&mut self) -> io::Result<(u16, Vec<u8>)>;
}

const CHUNK: usize = 64;

/// Codec v1 as 64-byte chunks: `?##` + `>HL` header on the first, `?` on each following one.
pub fn chunks(id: u16, payload: &[u8]) -> Vec<[u8; CHUNK]> {
    let mut stream = b"##".to_vec();
    stream.extend_from_slice(&id.to_be_bytes());
    stream.extend_from_slice(&(payload.len() as u32).to_be_bytes());
    stream.extend_from_slice(payload);
    stream
        .chunks(CHUNK - 1)
        .map(|part| {
            let mut chunk = [0u8; CHUNK];
            chunk[0] = b'?';
            chunk[1..=part.len()].copy_from_slice(part);
            chunk
        })
        .collect()
}

/// Reassemble a message from chunks handed in one at a time; `None` until it is complete.
#[derive(Default)]
pub struct Reassembly {
    header: Option<(u16, usize)>,
    buffer: Vec<u8>,
}

impl Reassembly {
    pub fn push(&mut self, chunk: &[u8]) -> io::Result<Option<(u16, Vec<u8>)>> {
        let bad = || io::Error::new(io::ErrorKind::InvalidData, "missing chunk magic");
        match self.header {
            None => {
                if chunk.len() < 9 || &chunk[..3] != b"?##" {
                    return Err(bad());
                }
                let id = u16::from_be_bytes([chunk[3], chunk[4]]);
                let len = u32::from_be_bytes([chunk[5], chunk[6], chunk[7], chunk[8]]) as usize;
                self.header = Some((id, len));
                self.buffer.extend_from_slice(&chunk[9..]);
            }
            Some(_) => {
                if chunk.first() != Some(&b'?') {
                    return Err(bad());
                }
                self.buffer.extend_from_slice(&chunk[1..]);
            }
        }
        let (id, len) = self.header.unwrap();
        if self.buffer.len() >= len {
            let mut payload = std::mem::take(&mut self.buffer);
            payload.truncate(len);
            self.header = None;
            return Ok(Some((id, payload)));
        }
        Ok(None)
    }
}

/// The emulator's UDP transport (default `127.0.0.1:21324`).
pub struct UdpEmulator {
    socket: UdpSocket,
}

impl UdpEmulator {
    pub fn connect(addr: &str) -> io::Result<Self> {
        let socket = UdpSocket::bind("127.0.0.1:0")?;
        socket.connect(addr)?;
        socket.set_read_timeout(Some(Duration::from_secs(300)))?;
        Ok(UdpEmulator { socket })
    }
}

impl FrameIo for UdpEmulator {
    fn write(&mut self, id: u16, payload: &[u8]) -> io::Result<()> {
        for chunk in chunks(id, payload) {
            self.socket.send(&chunk)?;
        }
        Ok(())
    }

    fn read(&mut self) -> io::Result<(u16, Vec<u8>)> {
        let mut reassembly = Reassembly::default();
        let mut chunk = [0u8; CHUNK];
        loop {
            let n = self.socket.recv(&mut chunk)?;
            if let Some(message) = reassembly.push(&chunk[..n])? {
                return Ok(message);
            }
        }
    }
}

/// A [`WardPipe`] over any [`FrameIo`].
///
/// HANDLES WHAT THE USER IS PART OF: a `ButtonRequest` is acked (the user acts on the device), a
/// `PassphraseRequest` is answered with [`CodecPipe::passphrase`] if one was set and refused
/// otherwise -- answering an empty passphrase on the user's behalf would open a different wallet.
/// Everything else, the WARD pulls included, is returned.
pub struct CodecPipe<T: FrameIo> {
    io: T,
    pub passphrase: Option<String>,
}

impl<T: FrameIo> CodecPipe<T> {
    pub fn new(io: T) -> Self {
        CodecPipe { io, passphrase: None }
    }

    pub fn into_inner(self) -> T {
        self.io
    }

    /// Open the session: `Initialize`, answered with `Features`.
    pub fn initialize(&mut self) -> Result<Value, PipeError> {
        let (name, features) = self.exchange("Initialize", &json!({}))?;
        if name != "Features" {
            return Err(PipeError::Other(format!("Initialize answered {name}")));
        }
        Ok(features)
    }

    fn exchange(&mut self, name: &str, body: &Value) -> Result<(String, Value), PipeError> {
        let (mut name, mut body) = (name.to_owned(), body.clone());
        loop {
            let (id, bytes) = encode(&name, &body).map_err(PipeError::Other)?;
            self.io.write(id, &bytes).map_err(|e| PipeError::Other(e.to_string()))?;
            let (id, bytes) = self.io.read().map_err(|e| PipeError::Other(e.to_string()))?;
            let (reply, message) = decode(id, &bytes).map_err(PipeError::Other)?;
            match reply.as_str() {
                "ButtonRequest" => (name, body) = ("ButtonAck".into(), json!({})),
                "PassphraseRequest" => match &self.passphrase {
                    Some(p) => (name, body) = ("PassphraseAck".into(), json!({ "passphrase": p })),
                    None => return Err(PipeError::Other("the device asks for a passphrase".into())),
                },
                "Failure" => {
                    return Err(PipeError::Failure {
                        code: message.get("code").and_then(Value::as_str).map(str::to_owned),
                        message: message
                            .get("message")
                            .and_then(Value::as_str)
                            .unwrap_or_default()
                            .to_owned(),
                    })
                }
                _ => return Ok((reply, message)),
            }
        }
    }
}

impl<T: FrameIo> WardPipe for CodecPipe<T> {
    async fn call(&mut self, name: &str, message: Value) -> Result<(String, Value), PipeError> {
        self.exchange(name, &message)
    }
}
