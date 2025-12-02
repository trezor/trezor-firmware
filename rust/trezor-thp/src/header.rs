use crate::Role;
use crate::alternating_bit::SyncBits;
use crate::control_byte::{self, ControlByte};
use crate::crc32;
use crate::error::{self, Error, Result};

use core::marker::PhantomData;

const CHECKSUM_LEN: u16 = crc32::CHECKSUM_LEN as u16;
const NONCE_LEN: u16 = 8;
const MAX_PAYLOAD_LEN: u16 = 60000;

const MAX_CHANNEL_ID: u16 = 0xFFEF;
const BROADCAST_CHANNEL_ID: u16 = 0xFFFF;

/// Represents packet header, i.e. control byte, channel id and possibly payload length.
/// Please note that `seq_bit` and `ack_bit` which are also part of the header are handled separately.
#[derive(Clone, Debug, PartialEq)]
pub enum Header<R: Role> {
    Continuation {
        channel_id: u16,
    },
    Ack {
        channel_id: u16,
        _phantom: PhantomData<R>,
    },
    CodecV1Request {
        is_continuation: bool,
    },
    CodecV1Response,
    ChannelAllocationRequest,
    ChannelAllocationResponse {
        payload_len: u16,
    },
    TransportError {
        channel_id: u16,
        // FIXME not serialized in to_bytes, probably should not be here
        error_code: error::TransportError,
    },
    Ping,
    Pong,
    Handshake {
        phase: HandshakeMessage,
        channel_id: u16,
        payload_len: u16,
    },
    Encrypted {
        channel_id: u16,
        payload_len: u16,
    },
}

#[derive(Clone, Debug, PartialEq)]
pub enum HandshakeMessage {
    InitiationRequest,
    InitiationResponse,
    CompletionRequest,
    CompletionResponse,
}

pub const fn channel_id_valid(channel_id: u16) -> bool {
    channel_id <= MAX_CHANNEL_ID || channel_id == BROADCAST_CHANNEL_ID
}

fn parse_u16(buffer: &[u8]) -> Result<(u16, &[u8])> {
    let (bytes, rest) = buffer
        .split_first_chunk::<2>()
        .ok_or(Error::MalformedData)?;
    Ok((u16::from_be_bytes(*bytes), rest))
}

impl<R: Role> Header<R> {
    const INIT_LEN: usize = 5;
    const CONT_LEN: usize = 3;

    /// Parse header from a byte slice. Return remaining subslice on success.
    /// Note: sync bits are discarded and need to be obtained from input buffer separately.
    pub fn parse(buffer: &[u8]) -> Result<(Self, &[u8])> {
        let (first_byte, rest) = buffer.split_first().ok_or(Error::MalformedData)?;
        let cb = ControlByte::from(*first_byte);
        if cb.is_codec_v1() {
            if R::is_host() {
                return Ok((Header::CodecV1Response, &[]));
            } else {
                let is_continuation = !matches!(rest.get(..2), Some(b"##"));
                return Ok((Header::CodecV1Request { is_continuation }, &[]));
            }
        }
        let (channel_id, rest) = parse_u16(rest)?;
        if !channel_id_valid(channel_id) {
            return Err(Error::OutOfBounds);
        }
        if cb.is_continuation() {
            return Ok((Header::Continuation { channel_id }, rest));
        }
        let (payload_len, rest) = parse_u16(rest)?;
        if payload_len > MAX_PAYLOAD_LEN {
            return Err(Error::OutOfBounds);
        }
        // strip padding if there is any
        let without_padding = rest.len().min(payload_len.into());
        let rest = &rest[..without_padding];
        if let Some(fixed) = Self::parse_fixed(buffer, cb, channel_id, payload_len)? {
            return Ok((fixed, rest));
        }
        if let Some(phase) = HandshakeMessage::from_u8::<R>(cb.into()) {
            return Ok((
                Self::Handshake {
                    phase,
                    channel_id,
                    payload_len,
                },
                rest,
            ));
        }
        if cb.is_encrypted_transport() {
            return Ok((
                Self::Encrypted {
                    channel_id,
                    payload_len,
                },
                rest,
            ));
        }
        if R::is_host() && channel_id == BROADCAST_CHANNEL_ID && cb.is_channel_allocation_response()
        {
            return Ok((Self::ChannelAllocationResponse { payload_len }, rest));
        }
        Err(Error::MalformedData)
    }

    fn parse_fixed(
        buffer: &[u8],
        cb: ControlByte,
        channel_id: u16,
        payload_len: u16,
    ) -> Result<Option<Self>> {
        let res = if cb.is_ack() {
            Self::Ack {
                channel_id,
                _phantom: PhantomData,
            }
        } else if cb.is_error() {
            Self::TransportError {
                channel_id,
                error_code: error::TransportError::from(
                    *buffer.get(Self::INIT_LEN).ok_or(Error::MalformedData)?,
                ),
            }
        } else if channel_id == BROADCAST_CHANNEL_ID {
            if cb.is_channel_allocation_request() && !R::is_host() {
                Header::ChannelAllocationRequest
            } else if cb.is_ping() && !R::is_host() {
                Header::Ping
            } else if cb.is_pong() && R::is_host() {
                Header::Pong
            } else {
                return Ok(None);
            }
        } else {
            return Ok(None);
        };
        if res.payload_len() == payload_len {
            Ok(Some(res))
        } else {
            Err(Error::MalformedData)
        }
    }

    fn control_byte(&self, sync_bits: SyncBits) -> Option<ControlByte> {
        let cb = match self {
            Self::Continuation { .. } => control_byte::CONTINUATION_PACKET,
            Self::Ack { .. } => control_byte::ACK_MESSAGE,
            Self::ChannelAllocationRequest if R::is_host() => control_byte::CHANNEL_ALLOCATION_REQ,
            Self::ChannelAllocationResponse { .. } if !R::is_host() => {
                control_byte::CHANNEL_ALLOCATION_RES
            }
            Self::TransportError { .. } => control_byte::ERROR,
            Self::Ping if R::is_host() => control_byte::PING,
            Self::Pong if !R::is_host() => control_byte::PONG,
            Self::Handshake { phase, .. } => phase.to_u8::<R>()?,
            Self::Encrypted { .. } => control_byte::ENCRYPTED_TRANSPORT,
            _ => return None,
        };
        let mut cb = ControlByte::from(cb);
        if self.is_ack() && sync_bits.seq_bit() {
            // ACK has no seq_bit
            return None;
        } else if self.is_ack() || self.is_encrypted() || self.is_handshake() {
            cb = cb.with_sync_bits(sync_bits)
        }
        Some(cb)
    }

    /// Serialize header to a buffer. Returns length of the result on success.
    pub fn to_bytes(&self, sync_bits: SyncBits, dest: &mut [u8]) -> Option<usize> {
        if let Self::Continuation { channel_id } = self {
            return if dest.len() < Self::CONT_LEN {
                None
            } else {
                dest[0] = control_byte::CONTINUATION_PACKET;
                dest[1..3].copy_from_slice(&channel_id.to_be_bytes());
                Some(Self::CONT_LEN)
            };
        }
        if dest.len() < Self::INIT_LEN {
            return None;
        }
        let length = self.payload_len();
        dest[0] = self.control_byte(sync_bits)?.into();
        dest[1..3].copy_from_slice(&self.channel_id().to_be_bytes());
        dest[3..5].copy_from_slice(&length.to_be_bytes());
        Some(Self::INIT_LEN)
    }

    pub const fn channel_id(&self) -> u16 {
        match self {
            Self::Continuation { channel_id } => *channel_id,
            Self::Ack { channel_id, .. } => *channel_id,
            Self::TransportError { channel_id, .. } => *channel_id,
            Self::Handshake {
                phase: _,
                channel_id,
                ..
            } => *channel_id,
            Self::Encrypted { channel_id, .. } => *channel_id,
            _ => BROADCAST_CHANNEL_ID,
        }
    }

    /// Payload length including checksum. Messages without checksum return 0.
    pub const fn payload_len(&self) -> u16 {
        match self {
            Self::Continuation { .. } => 0,
            Self::Ack { .. } => CHECKSUM_LEN,
            Self::CodecV1Request { .. } | Self::CodecV1Response => 0,
            Self::ChannelAllocationRequest => NONCE_LEN + CHECKSUM_LEN,
            Self::ChannelAllocationResponse { payload_len } => *payload_len,
            Self::TransportError { .. } => 1 + CHECKSUM_LEN,
            Self::Ping => NONCE_LEN + CHECKSUM_LEN,
            Self::Pong => NONCE_LEN + CHECKSUM_LEN,
            Self::Handshake {
                phase: _,
                channel_id: _,
                payload_len,
            } => *payload_len,
            Self::Encrypted {
                channel_id: _,
                payload_len,
            } => *payload_len,
        }
    }

    pub const fn header_len(&self) -> usize {
        match self {
            Self::Continuation { .. } => Self::CONT_LEN,
            _ => Self::INIT_LEN,
        }
    }

    pub const fn new_continuation(channel_id: u16) -> Self {
        Self::Continuation { channel_id }
    }

    pub const fn new_encrypted(channel_id: u16, payload: &[u8]) -> Self {
        // FIXME validate payload length, channel id?
        Self::Encrypted {
            channel_id,
            payload_len: payload.len() as u16 + CHECKSUM_LEN,
        }
    }

    pub const fn new_error(channel_id: u16, error_code: error::TransportError) -> Self {
        Self::TransportError {
            channel_id,
            error_code,
        }
    }

    pub const fn new_ack(channel_id: u16) -> Self {
        Self::Ack {
            channel_id,
            _phantom: PhantomData,
        }
    }

    pub const fn new_ping() -> Self {
        Self::Ping
    }

    pub const fn new_pong() -> Self {
        Self::Pong
    }

    pub const fn is_continuation(&self) -> bool {
        matches!(self, Self::Continuation { .. })
    }

    pub const fn is_ping(&self) -> bool {
        matches!(self, Self::Ping)
    }

    pub const fn is_pong(&self) -> bool {
        matches!(self, Self::Pong)
    }

    pub const fn is_handshake(&self) -> bool {
        matches!(self, Self::Handshake { .. })
    }

    pub const fn is_encrypted(&self) -> bool {
        matches!(self, Self::Encrypted { .. })
    }

    pub const fn is_ack(&self) -> bool {
        matches!(self, Self::Ack { .. })
    }
}

impl HandshakeMessage {
    pub fn from_u8<R: Role>(val: u8) -> Option<Self> {
        let masked = val & control_byte::DATA_MASK;
        Some(match masked {
            control_byte::HANDSHAKE_INIT_REQ if !R::is_host() => {
                HandshakeMessage::InitiationRequest
            }
            control_byte::HANDSHAKE_INIT_RES if R::is_host() => {
                HandshakeMessage::InitiationResponse
            }
            control_byte::HANDSHAKE_COMP_REQ if !R::is_host() => {
                HandshakeMessage::CompletionRequest
            }
            control_byte::HANDSHAKE_COMP_RES if R::is_host() => {
                HandshakeMessage::CompletionResponse
            }
            _ => return None,
        })
    }

    pub fn to_u8<R: Role>(&self) -> Option<u8> {
        Some(match self {
            HandshakeMessage::InitiationRequest if R::is_host() => control_byte::HANDSHAKE_INIT_REQ,
            HandshakeMessage::InitiationResponse if !R::is_host() => {
                control_byte::HANDSHAKE_INIT_RES
            }
            HandshakeMessage::CompletionRequest if R::is_host() => control_byte::HANDSHAKE_COMP_REQ,
            HandshakeMessage::CompletionResponse if !R::is_host() => {
                control_byte::HANDSHAKE_COMP_RES
            }
            _ => return None,
        })
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use crate::error::TransportError;
    use crate::{Device, Host};

    impl<R: Role> Header<R> {
        fn transmute<S: Role>(&self) -> Header<S> {
            let s = self.clone();
            match s {
                Self::Continuation { channel_id } => Header::<S>::Continuation { channel_id },
                Self::Ack { channel_id, .. } => Header::<S>::Ack {
                    channel_id,
                    _phantom: PhantomData,
                },
                Self::CodecV1Request { is_continuation } => {
                    Header::<S>::CodecV1Request { is_continuation }
                }
                Self::CodecV1Response => Header::<S>::CodecV1Response,
                Self::ChannelAllocationRequest => Header::<S>::ChannelAllocationRequest,
                Self::ChannelAllocationResponse { payload_len } => {
                    Header::<S>::ChannelAllocationResponse { payload_len }
                }
                Self::TransportError {
                    channel_id,
                    error_code,
                } => Header::<S>::TransportError {
                    channel_id,
                    error_code,
                },
                Self::Ping => Header::<S>::Ping,
                Self::Pong => Header::<S>::Pong,
                Self::Handshake {
                    phase,
                    channel_id,
                    payload_len,
                } => Header::<S>::Handshake {
                    phase,
                    channel_id,
                    payload_len,
                },
                Self::Encrypted {
                    channel_id,
                    payload_len,
                } => Header::<S>::Encrypted {
                    channel_id,
                    payload_len,
                },
            }
        }
    }

    const VECTORS_GOOD: &[(&str, Header<Device>)] = &[
        ("801234", Header::Continuation { channel_id: 0x1234 }),
        (
            "80ffff",
            Header::Continuation {
                channel_id: BROADCAST_CHANNEL_ID,
            },
        ),
        ("8012345678", Header::Continuation { channel_id: 0x1234 }),
        ("201337000463061764", Header::new_ack(0x1337)),
        ("20ffff000460132e1c", Header::new_ack(BROADCAST_CHANNEL_ID)),
        (
            "041337000457479ea0",
            Header::Encrypted {
                channel_id: 0x1337,
                payload_len: 4,
            },
        ),
        (
            "041337000457479ea0041337000457479ea0",
            Header::Encrypted {
                channel_id: 0x1337,
                payload_len: 4,
            },
        ),
        (
            "42ffff000502744a5ed00000",
            Header::TransportError {
                channel_id: BROADCAST_CHANNEL_ID,
                error_code: TransportError::UnallocatedChannel,
            },
        ),
        (
            "4213370005022a97b2e7",
            Header::TransportError {
                channel_id: 0x1337,
                error_code: TransportError::UnallocatedChannel,
            },
        ),
    ];

    #[test]
    fn test_parse_good() {
        for (input, expected) in VECTORS_GOOD {
            let input = hex::decode(input).unwrap();
            let (header_device, _) = Header::<Device>::parse(&input).expect("parse1");
            assert_eq!(header_device, *expected);
            let (header_host, _) = Header::<Host>::parse(&input).expect("parse2");
            assert_eq!(header_host, expected.transmute());
        }
    }

    #[test]
    fn test_serialize() {
        for (bytes, header) in VECTORS_GOOD {
            let bytes = hex::decode(bytes).unwrap();
            let mut buffer = [0u8; 256];
            let sb = SyncBits::new();
            let len = header.to_bytes(sb, &mut buffer).expect("to_bytes1");
            assert!(len > 0);
            assert_eq!(&buffer[..len], &bytes[..len]);
            let len = header
                .transmute::<Host>()
                .to_bytes(sb, &mut buffer)
                .expect("to_bytes2");
            assert!(len > 0);
            assert_eq!(&buffer[..len], &bytes[..len]);
        }
    }

    #[test]
    fn test_serialize_sync() {
        for (bytes, header) in VECTORS_GOOD {
            if !header.is_encrypted() && !header.is_handshake() {
                continue; // no sync bits
            }
            let bytes = hex::decode(bytes).unwrap();
            let mut buffer = [0u8; 256];
            let sb = SyncBits::new().with_seq_bit(true);
            let len = header.to_bytes(sb, &mut buffer).expect("to_bytes");
            assert!(len > 0);
            assert_ne!(&buffer[..len], &bytes[..len]);
        }
    }

    const VECTORS_GOOD_DEVICE: &[(&str, Header<Device>)] = &[
        // ("3f2323", Header::CodecV1Request { is_continuation: false }),
        // ("3f6666", Header::CodecV1Request { is_continuation: true }),
        (
            "40ffff000caaaaaaaaaaaaaaaab67b3b6b",
            Header::ChannelAllocationRequest,
        ),
        ("43ffff000cbaaaaaaaaaaaaaaa770a668e", Header::Ping),
        (
            "00000f000cbaaaaaaaaaaaaaaac8978de2",
            Header::Handshake {
                phase: HandshakeMessage::InitiationRequest,
                channel_id: 0x000f,
                payload_len: 12,
            },
        ),
        (
            "02000f000cff00ff00aaaaaaaa4cb96673",
            Header::Handshake {
                phase: HandshakeMessage::CompletionRequest,
                channel_id: 0x000f,
                payload_len: 12,
            },
        ),
    ];

    #[test]
    fn test_role_device() {
        for (bytes, header) in VECTORS_GOOD_DEVICE {
            let bytes = hex::decode(bytes).unwrap();
            let (parsed_header, _) = Header::<Device>::parse(&bytes).expect("parse");
            assert_eq!(parsed_header, *header);
            let res = Header::<Host>::parse(&bytes);
            assert!(res.is_err());

            let mut buffer = [0u8; 256];
            let sb = SyncBits::new();
            let len = header
                .transmute::<Host>()
                .to_bytes(sb, &mut buffer)
                .expect("to_bytes");
            assert!(len > 0);
            assert_eq!(&buffer[..len], &bytes[..len]);
            let res = header.to_bytes(sb, &mut buffer);
            assert!(res.is_none());
        }
    }

    const VECTORS_GOOD_HOST: &[(&str, Header<Host>)] = &[
        (
            "41ffff029aaaaaaaaaaaaaaaaab67b3b6b",
            Header::ChannelAllocationResponse { payload_len: 666 },
        ),
        ("44ffff000cbaaaaaaaaaaaaaaa770a668e", Header::Pong),
        (
            "01000f000cbaaaaaaaaaaaaaaac8978de2",
            Header::Handshake {
                phase: HandshakeMessage::InitiationResponse,
                channel_id: 0x000f,
                payload_len: 12,
            },
        ),
        (
            "03000f000cff00ff00aaaaaaaa4cb96673",
            Header::Handshake {
                phase: HandshakeMessage::CompletionResponse,
                channel_id: 0x000f,
                payload_len: 12,
            },
        ),
    ];

    #[test]
    fn test_role_host() {
        for (bytes, header) in VECTORS_GOOD_HOST {
            let bytes = hex::decode(bytes).unwrap();
            let (parsed_header, _) = Header::<Host>::parse(&bytes).expect("parse");
            assert_eq!(parsed_header, *header);
            let res = Header::<Device>::parse(&bytes);
            assert!(res.is_err());

            let mut buffer = [0u8; 256];
            let sb = SyncBits::new();
            let len = header
                .transmute::<Device>()
                .to_bytes(sb, &mut buffer)
                .expect("to_bytes");
            assert!(len > 0);
            assert_eq!(&buffer[..len], &bytes[..len]);
            let res = header.to_bytes(sb, &mut buffer);
            assert!(res.is_none());
        }
    }

    const VECTORS_BAD_SHORT: &[&str] = &[
        "", "00", "04", "80", "39", "0000", "0400", "8000", "4f6f", "040000", "04000000",
        "42000000", "00000000",
    ];

    const VECTORS_BAD: &[&str] = &[
        "7f00000000", // bad control byte
        "04fff00001", // bad channel id
        "041111ffee", // invalid length field
        "80fffe0000", // bad channel id
    ];

    #[test]
    fn test_parse_bad() {
        for v in VECTORS_BAD_SHORT.iter().chain(VECTORS_BAD) {
            let v = hex::decode(v).unwrap();
            let res = Header::<Device>::parse(&v);
            assert!(res.is_err());
            let res = Header::<Host>::parse(&v);
            assert!(res.is_err());
        }
    }
}
