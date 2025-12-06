use crate::alternating_bit::SyncBits;

pub const CODEC_V1: u8 = 0x3F;
pub const CONTINUATION_PACKET: u8 = 0x80;

pub const CONTINUATION_PACKET_MASK: u8 = 0x80;

pub const ACK_MASK: u8 = 0xF7;
pub const ACK_MESSAGE: u8 = 0x20;

pub const DATA_MASK: u8 = 0xE7;
pub const HANDSHAKE_INIT_REQ: u8 = 0x00;
pub const HANDSHAKE_INIT_RES: u8 = 0x01;
pub const HANDSHAKE_COMP_REQ: u8 = 0x02;
pub const HANDSHAKE_COMP_RES: u8 = 0x03;
pub const ENCRYPTED_TRANSPORT: u8 = 0x04;

pub const CHANNEL_ALLOCATION_REQ: u8 = 0x40;
pub const CHANNEL_ALLOCATION_RES: u8 = 0x41;
pub const ERROR: u8 = 0x42;
pub const PING: u8 = 0x43;
pub const PONG: u8 = 0x44;

pub const ACK_BIT: u8 = 0x08;
pub const SEQ_BIT: u8 = 0x10;
pub const SYNC_MASK: u8 = ACK_BIT | SEQ_BIT;

#[derive(Clone, Copy)]
pub struct ControlByte(u8);

impl ControlByte {
    pub fn sync_bits(&self) -> SyncBits {
        SyncBits::from(self.0 & SYNC_MASK)
    }

    pub fn with_sync_bits(self, sb: SyncBits) -> Self {
        Self(self.0 & !SYNC_MASK | <SyncBits as Into<u8>>::into(sb))
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
}

// Note consider TryFrom + validation
impl From<u8> for ControlByte {
    fn from(byte: u8) -> Self {
        Self(byte)
    }
}

impl From<ControlByte> for u8 {
    fn from(cb: ControlByte) -> Self {
        cb.0
    }
}
