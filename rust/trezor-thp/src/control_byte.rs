use crate::{alternating_bit::SyncBits, error::Error, header::HandshakeMessage};

const CODEC_V1: u8 = 0x3F;
const CONTINUATION_PACKET: u8 = 0x80;

const CONTINUATION_PACKET_MASK: u8 = 0x80;

const ACK_MASK: u8 = 0xF7;
const ACK_MESSAGE: u8 = 0x20;
const DATA_MASK: u8 = 0xE7;
const HANDSHAKE_INIT_REQ: u8 = 0x00;
const HANDSHAKE_INIT_RES: u8 = 0x01;
const HANDSHAKE_COMP_REQ: u8 = 0x02;
const HANDSHAKE_COMP_RES: u8 = 0x03;
const ENCRYPTED_TRANSPORT: u8 = 0x04;

const CHANNEL_ALLOCATION_REQ: u8 = 0x40;
const CHANNEL_ALLOCATION_RES: u8 = 0x41;
const ERROR: u8 = 0x42;
const PING: u8 = 0x43;
const PONG: u8 = 0x44;

pub const ACK_BIT: u8 = 0x08;
pub const SEQ_BIT: u8 = 0x10;
pub const SYNC_MASK: u8 = ACK_BIT | SEQ_BIT;

#[derive(Clone, Copy)]
pub struct ControlByte(u8);

impl ControlByte {
    pub const fn codec_v1() -> Self {
        Self(CODEC_V1)
    }

    pub const fn continuation() -> Self {
        Self(CONTINUATION_PACKET)
    }

    pub const fn ack() -> Self {
        Self(ACK_MESSAGE)
    }

    pub const fn encrypted_transport() -> Self {
        Self(ENCRYPTED_TRANSPORT)
    }

    pub const fn ping() -> Self {
        Self(PING)
    }

    pub const fn pong() -> Self {
        Self(PONG)
    }

    pub const fn error() -> Self {
        Self(ERROR)
    }

    pub const fn channel_allocation_request() -> Self {
        Self(CHANNEL_ALLOCATION_REQ)
    }

    pub const fn channel_allocation_response() -> Self {
        Self(CHANNEL_ALLOCATION_RES)
    }

    pub const fn handshake(phase: HandshakeMessage) -> Self {
        match phase {
            HandshakeMessage::InitiationRequest => Self(HANDSHAKE_INIT_REQ),
            HandshakeMessage::InitiationResponse => Self(HANDSHAKE_INIT_RES),
            HandshakeMessage::CompletionRequest => Self(HANDSHAKE_COMP_REQ),
            HandshakeMessage::CompletionResponse => Self(HANDSHAKE_COMP_RES),
        }
    }

    pub const fn is_ack(&self) -> bool {
        self.0 & ACK_MASK == ACK_MESSAGE
    }

    pub const fn is_continuation(&self) -> bool {
        self.0 & CONTINUATION_PACKET_MASK == CONTINUATION_PACKET
    }

    pub const fn is_encrypted_transport(&self) -> bool {
        self.0 & DATA_MASK == ENCRYPTED_TRANSPORT
    }

    pub const fn is_codec_v1(&self) -> bool {
        self.0 == CODEC_V1
    }

    pub const fn is_ping(&self) -> bool {
        self.0 == PING
    }

    pub const fn is_pong(&self) -> bool {
        self.0 == PONG
    }

    pub const fn is_error(&self) -> bool {
        self.0 == ERROR
    }

    pub const fn is_channel_allocation_request(&self) -> bool {
        self.0 == CHANNEL_ALLOCATION_REQ
    }

    pub const fn is_channel_allocation_response(&self) -> bool {
        self.0 == CHANNEL_ALLOCATION_RES
    }

    pub const fn is_handshake(&self) -> bool {
        self.handshake_phase().is_some()
    }

    pub const fn handshake_phase(&self) -> Option<HandshakeMessage> {
        let res = match self.0 & DATA_MASK {
            HANDSHAKE_INIT_REQ => HandshakeMessage::InitiationRequest,
            HANDSHAKE_INIT_RES => HandshakeMessage::InitiationResponse,
            HANDSHAKE_COMP_REQ => HandshakeMessage::CompletionRequest,
            HANDSHAKE_COMP_RES => HandshakeMessage::CompletionResponse,
            _ => return None,
        };
        Some(res)
    }

    pub fn sync_bits(&self) -> SyncBits {
        SyncBits::from(self.0)
    }

    pub fn with_sync_bits(self, sb: SyncBits) -> Self {
        Self(self.0 & !SYNC_MASK | <SyncBits as Into<u8>>::into(sb))
    }
}

impl TryFrom<u8> for ControlByte {
    type Error = Error;

    fn try_from(byte: u8) -> Result<Self, Error> {
        let cb = Self(byte);
        let valid = cb.is_continuation()
            || cb.is_ack()
            || cb.is_encrypted_transport()
            || cb.is_error()
            || cb.is_ping()
            || cb.is_pong()
            || cb.is_channel_allocation_request()
            || cb.is_channel_allocation_response()
            || cb.is_handshake()
            || cb.is_codec_v1();
        if !valid {
            log::warn!("Invalid control byte {}.", byte);
            return Err(Error::malformed_data());
        }
        Ok(cb)
    }
}

impl From<ControlByte> for u8 {
    fn from(cb: ControlByte) -> Self {
        cb.0
    }
}
