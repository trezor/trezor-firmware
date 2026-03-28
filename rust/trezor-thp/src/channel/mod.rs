#[cfg(feature = "use_std")]
pub mod buffered;
pub mod device;
pub mod host;
mod noise;
#[cfg(test)]
mod test;

use crate::{
    Error, Role,
    alternating_bit::{ChannelSync, SyncBits},
    error::{Result, TransportError},
    fragment::{Fragmenter, Reassembler},
    header::{BROADCAST_CHANNEL_ID, Header, NONCE_LEN, parse_cb_channel, parse_u16},
};

use noise::NoiseCiphers;
pub use noise::{
    Backend, Cipher, DH, HANDSHAKE_HASH_LEN, Hash, PRIVKEY_LEN, PUBKEY_LEN, TAG_LEN, U8Array,
};

const APP_HEADER_LEN: usize = 3; // session id (1) + message type (2)

/// Used during channel allocation on broadcast channel.
#[derive(Copy, Clone, PartialEq, Eq)]
struct Nonce([u8; NONCE_LEN as _]);

impl Nonce {
    pub const LEN: usize = NONCE_LEN as _;

    pub fn random<B: Backend>() -> Self {
        let mut bytes = [0u8; Self::LEN];
        B::random_bytes(&mut bytes);
        Self(bytes)
    }

    pub fn parse(bytes: &[u8]) -> Result<(Self, &[u8])> {
        bytes
            .split_first_chunk::<{ Nonce::LEN }>()
            .map(|(n, p)| (Nonce(*n), p))
            .ok_or_else(Error::malformed_data)
    }

    pub fn as_slice(&self) -> &[u8] {
        &self.0
    }
}

/// Sent by device after successful handshake to indicate whether pairing is required.
#[repr(u8)]
#[derive(Copy, Clone, PartialEq, Eq)]
pub enum PairingState {
    Unpaired = 0,
    Paired = 1,
    PairedAutoconnect = 2,
}

impl PairingState {
    pub fn is_paired(&self) -> bool {
        !matches!(self, Self::Unpaired)
    }
}

impl TryFrom<&[u8]> for PairingState {
    type Error = Error;

    fn try_from(bytes: &[u8]) -> Result<Self> {
        Ok(match bytes {
            [n] => PairingState::try_from(*n)?,
            _ => return Err(Error::malformed_data()),
        })
    }
}

impl TryFrom<u8> for PairingState {
    type Error = Error;

    fn try_from(val: u8) -> Result<Self> {
        Ok(match val {
            0 => Self::Unpaired,
            1 => Self::Paired,
            2 => Self::PairedAutoconnect,
            _ => return Err(Error::malformed_data()),
        })
    }
}

impl From<PairingState> for u8 {
    fn from(pairing_state: PairingState) -> Self {
        pairing_state as u8
    }
}

/// Is the channel currently sending or receiving a message?
enum ChannelState<R: Role> {
    /// Ready to send or receive.
    Idle,
    /// In the process of sending a message, or waiting for ACK.
    Sending {
        fragmenter: Fragmenter<R>,
        retry: u8,
    },
    /// About to send Transport error, these are not ACKed.
    /// Transitions to Failed afterwards unless the error is recoverable.
    SendingError { error: TransportError },
    /// In the process of receiving a message, or waiting for the consumer to pick up
    /// an assembled message.
    Receiving { reassembler: Reassembler<R> },
    /// Channel is inoperable.
    /// None: local failure
    /// Some: error message received from other side
    Failed { error: Option<TransportError> },
}

/// THP channel with established secure layer.
///
/// There is no constructor, to obtain a channel please use [`host::Mux`]
/// or [`device::Mux`].
/// For actually sending and receiving messages please see [`ChannelIO`].
pub struct Channel<R: Role, B: Backend> {
    channel_id: u16,
    sync: ChannelSync,
    noise: Option<NoiseCiphers<B>>,
    send_ack: Option<SyncBits>,
    state: ChannelState<R>,
    pairing_state: PairingState,
}

impl<R: Role, B: Backend> Channel<R, B> {
    fn new(channel_id: u16) -> Self {
        Self {
            channel_id,
            sync: ChannelSync::new(),
            noise: None,
            send_ack: None,
            state: ChannelState::Idle,
            pairing_state: PairingState::Unpaired,
        }
    }

    fn noise(&mut self) -> Result<&mut NoiseCiphers<B>> {
        self.noise.as_mut().ok_or_else(Error::unexpected_input)
    }

    pub fn channel_id(&self) -> u16 {
        self.channel_id
    }

    pub fn handshake_hash(&self) -> &[u8; HANDSHAKE_HASH_LEN] {
        self.noise.as_ref().unwrap().handshake_hash()
    }

    /// Returns the channel pairing state at the end of the handshake.
    /// This is read-only attribute to inform the application whether it needs to perform
    /// pairing, or can directly transition to encrypted transport state.
    pub fn handshake_pairing_state(&self) -> PairingState {
        self.pairing_state
    }

    pub fn remote_static_key(&self) -> &[u8; PUBKEY_LEN] {
        self.noise.as_ref().unwrap().remote_static_key()
    }

    pub fn is_failed(&self) -> bool {
        matches!(self.state, ChannelState::Failed { .. })
    }

    /// Return the retransmission attempt number (the first transmission returns 0),
    /// or `None` if the channel is currently not sending anything.
    pub fn sending_retry(&self) -> Option<u8> {
        match self.state {
            ChannelState::Sending { retry, .. } => Some(retry),
            _ => None,
        }
    }

    pub fn send_error(&mut self, error: TransportError) {
        self.state = ChannelState::SendingError { error };
    }

    fn raw_in(&mut self, header: Header<R>, send_buffer: &[u8]) -> Result<()> {
        let ChannelState::Idle = self.state else {
            return Err(Error::not_ready());
        };
        let sb = self.sync.send_start().ok_or_else(Error::not_ready)?;
        let fragmenter = Fragmenter::new(header, sb, send_buffer)?;
        self.state = ChannelState::Sending {
            fragmenter,
            retry: 0,
        };
        Ok(())
    }

    fn raw_out(&mut self, receive_buffer: &[u8]) -> Result<(Header<R>, usize)> {
        let ChannelState::Receiving { reassembler } = &mut self.state else {
            return Err(Error::not_ready());
        };
        if !reassembler.is_done() {
            return Err(Error::not_ready());
        }
        let len = match reassembler.verify(receive_buffer) {
            Ok(len) => len,
            Err(e) => {
                log::warn!(
                    "[{}] Reassembled message with invalid checksum.",
                    self.channel_id
                );
                return Err(e);
            }
        };
        self.send_ack = Some(self.sync.receive_acknowledge());
        let header = reassembler.header().clone();
        self.state = ChannelState::Idle;
        Ok((header, len))
    }

    fn handle_packet(
        &mut self,
        packet_buffer: &[u8],
        receive_buffer: &mut [u8],
    ) -> Result<PacketInResult> {
        let (cb, channel_id, _rest) = parse_cb_channel(packet_buffer)?;
        if channel_id != self.channel_id {
            log::warn!(
                "[{}] Invalid channel {}, ignoring.",
                self.channel_id,
                channel_id
            );
            return Err(Error::malformed_data());
        }
        if cb.is_ack() {
            self.handle_ack(packet_buffer)?;
            return Ok(PacketInResult::ack());
        } else if cb.is_error() {
            let te = self.handle_error(packet_buffer)?;
            return Ok(PacketInResult::transport_error(te));
        }
        let is_cont = cb.is_continuation();
        if !(is_cont || cb.is_handshake() || cb.is_encrypted_transport()) {
            // Channel allocation and codec v1 are handled by Mux.
            log::warn!(
                "[{}] Unexpected control byte {}.",
                self.channel_id,
                u8::from(cb)
            );
            return Err(Error::malformed_data());
        }
        Ok(match &mut self.state {
            // First fragment.
            ChannelState::Receiving { .. } | ChannelState::Idle if !is_cont => {
                let (is_done, enlarge) = self.handle_init(packet_buffer, receive_buffer)?;
                PacketInResult::accept(is_done).with_buffer(enlarge)
            }
            // Continuation fragments.
            ChannelState::Receiving { reassembler } => {
                reassembler.update(packet_buffer, receive_buffer)?;
                PacketInResult::accept(reassembler.is_done())
            }
            // Ignore unexpected continuations.
            ChannelState::Idle => return Err(Error::malformed_data()),
            // Might possibly happen when we've sent an ACK and it got lost.
            // We end up sending reply while the other side is retransmitting.
            // Is this recoverable?
            ChannelState::Sending { .. } => return Err(Error::malformed_data()),
            ChannelState::SendingError { .. } => return Err(Error::unexpected_input()),
            ChannelState::Failed { .. } => return Err(Error::unexpected_input()),
        })
    }

    fn handle_ack(&mut self, packet_buffer: &[u8]) -> Result<()> {
        if matches!(self.state, ChannelState::Sending { .. }) {
            let sb = SyncBits::try_from(packet_buffer)?;
            self.sync.send_mark_delivered(sb);
            if self.sync.can_send() {
                self.state = ChannelState::Idle;
                return Ok(());
            }
        }
        log::warn!("[{}] Unexpected ACK.", self.channel_id);
        Err(Error::malformed_data())
    }

    fn handle_error(&mut self, packet_buffer: &[u8]) -> Result<TransportError> {
        let mut err_buf = [0u8; 16];
        if let Ok((header, payload)) = Reassembler::<R>::single(packet_buffer, &mut err_buf) {
            if header.is_error() {
                if let Ok(te) = TransportError::try_from(payload) {
                    log::error!("[{}] Peer sent an error: {}.", self.channel_id, te as u8);
                    if !te.is_recoverable() {
                        self.state = ChannelState::Failed { error: Some(te) };
                    }
                    return Ok(te);
                } else {
                    log::error!(
                        "[{}] Peer sent unknown error {}.",
                        self.channel_id,
                        payload.first().unwrap_or(&0)
                    );
                }
            }
            self.state = ChannelState::Failed { error: None };
            return Err(Error::malformed_data());
        }
        log::warn!("[{}] Peer sent an error with invalid CRC.", self.channel_id);
        Err(Error::malformed_data())
    }

    fn handle_init(
        &mut self,
        packet_buffer: &[u8],
        receive_buffer: &mut [u8],
    ) -> Result<(bool, Option<u16>)> {
        let sb = SyncBits::try_from(packet_buffer)?;
        if !self.sync.receive_start(sb) {
            // Bad sync bit, drop this packet and continuations.
            log::debug!("[{}] Bad sync bit, ignoring packet.", self.channel_id);
            self.state = ChannelState::Idle;
            return Err(Error::malformed_data());
        }
        receive_buffer.fill(0);
        let reassembler = Reassembler::new(packet_buffer, receive_buffer)?;
        let is_done = reassembler.is_done();
        let payload_len = reassembler.header().payload_len();
        let enlarge = (usize::from(payload_len) > receive_buffer.len()).then_some(payload_len);
        if enlarge.is_some() {
            log::debug!(
                "Message is larger ({}) than receive buffer ({}), requesting reallocation.",
                payload_len,
                receive_buffer.len()
            );
        }
        self.state = ChannelState::Receiving { reassembler };
        Ok((is_done, enlarge))
    }
}

/// Whether channel state changed after calling [`ChannelIO::packet_in`].
#[cfg_attr(any(test, debug_assertions), derive(Debug))]
#[derive(PartialEq, Eq)]
#[non_exhaustive]
pub enum PacketInResult {
    /// Channel ingested the packet and updated its state.
    Accepted {
        /// True if the packet contained valid ACK and channel is ready to send next message.
        ack_received: bool,
        /// If true the event loop should schedule calling [`ChannelIO::message_out`].
        message_ready: bool,
        /// True if the packet was a valid keep-alive reply ("PONG") message.
        pong: bool,
    },
    /// Channel ingested the packet and started reassembling a message that is larger
    /// than the current receive buffer. Resize it (keep the initial part) or destroy the channel.
    EnlargeBuffer {
        /// True if the packet contained valid ACK and channel is ready to send next message.
        /// Reserved for ACK piggybacking.
        ack_received: bool,
        /// Message size including checksum, the minimum new size of receive buffer.
        buffer_size: u16,
    },
    /// Peer sent a `TRANSPORT_ERROR` message.
    TransportError {
        /// Error sent by the peer.
        error: TransportError,
    },
    /// Channel cannot process the packet, possibly because it was damaged in transit.
    /// Channel remains usable after this error.
    Ignored { error: Error },
    /// Channel became inoperable due to this packet. Event loop should destroy it.
    Failed { error: Error },
    /// This packet is addressed to different channel. Event loop should look up the channel
    /// by its ID and call its [`ChannelIO::packet_in`].
    /// Only [`device::Mux`] and [`host::Mux`] return this variant.
    Route {
        /// Channel id of the destination. Never a broadcast.
        channel_id: u16,
        //TODO
        // buffer_size: u16,
    },
    /// Channel allocation request/response was received. Event loop should call
    /// [`Mux::channel_alloc`] to create new channel object. Only [`device::Mux`] and [`host::Mux`]
    /// return this variant. There is no queue, do it before processing the next packet.
    ///
    /// On the device side, application is responsible for allocating unique ids. It can use
    /// [`device::ChannelIdAllocator`] but still must check the result for uniqueness.
    ChannelAllocation,
    /// Call [`device::ChannelOpen::set_static_key`] or [`device::ChannelOpen::send_device_locked`].
    /// Only [`device::ChannelOpen`] returns this variant.
    HandshakeKeyRequired { try_to_unlock: bool },
}

impl PacketInResult {
    const fn accept(message_ready: bool) -> Self {
        Self::Accepted {
            ack_received: false,
            message_ready,
            pong: false,
        }
    }

    const fn with_buffer(self, enlarge_receive_buffer: Option<u16>) -> Self {
        match enlarge_receive_buffer {
            Some(buffer_size) => Self::EnlargeBuffer {
                ack_received: self.got_ack(),
                buffer_size,
            },
            None => self,
        }
    }

    const fn ignore(error: Error) -> Self {
        Self::Ignored { error }
    }

    const fn ack() -> Self {
        Self::Accepted {
            ack_received: true,
            message_ready: false,
            pong: false,
        }
    }

    const fn transport_error(e: TransportError) -> Self {
        Self::TransportError { error: e }
    }

    const fn route(channel_id: u16) -> Self {
        Self::Route { channel_id }
    }

    const fn fail(error: Error) -> Self {
        Self::Failed { error }
    }

    const fn channel_allocation() -> Self {
        Self::ChannelAllocation
    }

    const fn pong() -> Self {
        Self::Accepted {
            ack_received: false,
            message_ready: false,
            pong: true,
        }
    }

    /// True if the received packet was valid ACK.
    pub const fn got_ack(&self) -> bool {
        match self {
            Self::Accepted { ack_received, .. } => *ack_received,
            Self::EnlargeBuffer { ack_received, .. } => *ack_received,
            _ => false,
        }
    }

    /// True if the received packet was the last fragment of incoming message.
    /// Event loop should call [`ChannelIO::message_out`]. The message is
    /// not guaranteed to be valid.
    pub const fn got_message(&self) -> bool {
        matches!(
            self,
            Self::Accepted {
                message_ready: true,
                ..
            }
        )
    }

    pub const fn got_channel(&self) -> bool {
        matches!(self, Self::ChannelAllocation)
    }

    pub const fn got_pong(&self) -> bool {
        matches!(self, Self::Accepted { pong: true, .. })
    }

    pub const fn got_transport_error(&self) -> bool {
        matches!(self, Self::TransportError { .. })
    }

    pub fn check_failed(self) -> Result<Self> {
        if let Self::Failed { error: e } = self {
            return Err(e);
        }
        Ok(self)
    }

    // Fold Result<PacketInResult> into PacketInResult, separating fatal and nonfatal errors.
    fn from_result(res: Result<Self>) -> Self {
        match res {
            Err(e)
                if matches!(
                    e,
                    Error::MalformedData | Error::InvalidChecksum | Error::NotReady
                ) =>
            {
                Self::ignore(e)
            }
            Err(e) => Self::fail(e),
            Ok(x) => x,
        }
    }
}

/// Trait for communicating over THP channel.
///
/// As we have distinct types for channels in different phases of being established,
/// they share this trait for doing I/O.
///
/// A channel is an object that consumes (USB, BLE, UDP) packets and produces application
/// messages (usually protobuf encoded), and also consumes such messages to produce packets.
/// It also needs to be notified when a messages takes too long to send and should to be
/// retransmitted.
///
/// To give the application freedom in handling precious buffers used during message
/// fragmentation and reassembly, channel does not keep ownership of them, instead they need
/// to be passed along every call.
pub trait ChannelIO {
    /// Session ID (1B) + message type (2B) + AEAD tag (16B).
    const BUFFER_OVERHEAD: usize = APP_HEADER_LEN + TAG_LEN;

    /// Pass incoming packet into a channel.
    ///
    /// Please note the caller should first check whether channel ID matches.
    ///
    /// If [`PacketInResult::got_message()`] of the returned value evaluates to true the application
    /// should call [`ChannelIO::packet_out`].
    fn packet_in(&mut self, packet_buffer: &[u8], receive_buffer: &mut [u8]) -> PacketInResult;

    /// Is channel ready to accept incoming packet?
    ///
    /// Only provided for completeness as the channel is always ready to drop unexpected packets.
    fn packet_in_ready(&self) -> bool {
        true
    }

    /// Write outgoing packet to `packet_buffer`. Returns [`Error::NotReady`] if there isn't one.
    fn packet_out(&mut self, packet_buffer: &mut [u8], send_buffer: &[u8]) -> Result<()>;

    /// Is channel ready to send a packet?
    fn packet_out_ready(&self) -> bool;

    /// Submit prepared send buffer to encrypt and fragment into packets.
    ///
    /// The message including the application header (session id, message type) is passed in
    /// `send_buffer`, occupying first `plaintext_len` bytes. There must be at least 16 more
    /// bytes in the buffer for the authentication tag.
    ///
    /// Instead of this function you can use [`Self::message_in_from`] to prepare the send
    /// buffer for you.
    ///
    /// Returns [`Error::NotReady`] if the channel hasn't finished sending the previous message
    /// (did not send all fragments or did not receive valid ACK), or if the channel is
    /// currently receiving.
    fn message_in(&mut self, plaintext_len: usize, send_buffer: &mut [u8]) -> Result<()>;

    /// Is channel ready to send next message?
    ///
    /// After calling [`Self::message_in`] this method returns `false` until valid ACK is received
    /// from the other side.
    fn message_in_ready(&self) -> bool;

    /// Pick up reassembled and decrypted message. The channel will send ACK packet afterwards.
    ///
    /// Returns [`Error::NotReady`] if there is no reassembled message.
    ///
    /// Returns [`Error::InvalidChecksum`] if message integrity failed. Usually the other side
    /// will retransmit the message.
    fn message_out<'a>(&mut self, receive_buffer: &'a mut [u8]) -> Result<(u8, u16, &'a [u8])>;

    /// Is there a reassembled incoming message ready?
    ///
    /// You can use [`PacketInResult::got_message`] instead of this method.
    ///
    /// Please note the incoming message may not be valid.
    fn message_out_ready(&self) -> bool; // unused

    /// Retransmit message previously submitted using [`Self::message_in`]. Does nothing if
    /// ACK was already received.
    /// The library does not limit the number of retries - application needs to decide when
    /// to abandon the channel.
    fn message_retransmit(&mut self) -> Result<()>;

    /// Submit message for channel to encrypt and fragment into packets.
    ///
    /// The length of `send_buffer` must be at least [`Self::BUFFER_OVERHEAD`] more
    /// than the message length.
    ///
    /// Returns [`Error::NotReady`] if the channel hasn't finished sending the previous message
    /// (did not send all fragments or did not receive valid ACK), or if the channel is
    /// currently receiving.
    fn message_in_from(
        &mut self,
        session_id: u8,
        message_type: u16,
        message: &[u8],
        send_buffer: &mut [u8],
    ) -> Result<()> {
        if !self.message_in_ready() {
            return Err(Error::not_ready());
        }
        let plaintext_len = message.len() + APP_HEADER_LEN;
        if send_buffer.len() < plaintext_len {
            return Err(Error::insufficient_buffer());
        }
        send_buffer[0] = session_id;
        send_buffer[1..3].copy_from_slice(&message_type.to_be_bytes());
        send_buffer[3..plaintext_len].copy_from_slice(message);
        self.message_in(plaintext_len, send_buffer)
    }
}

impl<R: Role, B: Backend> ChannelIO for Channel<R, B> {
    fn packet_in(&mut self, packet_buffer: &[u8], receive_buffer: &mut [u8]) -> PacketInResult {
        if self.is_failed() {
            return PacketInResult::fail(Error::unexpected_input());
        }
        let res = PacketInResult::from_result(self.handle_packet(packet_buffer, receive_buffer));
        if let PacketInResult::Failed { .. } = res {
            self.state = ChannelState::Failed { error: None };
        }
        res
    }

    fn packet_out(&mut self, packet_buffer: &mut [u8], send_buffer: &[u8]) -> Result<()> {
        // Send pending ACK.
        if let Some(sb) = self.send_ack.take() {
            let header = Header::<R>::new_ack(self.channel_id)?;
            Fragmenter::single(header, sb, &[], packet_buffer)?;
            return Ok(());
        }
        if let ChannelState::SendingError { error } = self.state {
            let header = Header::<R>::new_error(self.channel_id)?;
            Fragmenter::single(header, SyncBits::new(), &[error.into()], packet_buffer)?;
            if error.is_recoverable() {
                self.state = ChannelState::Idle;
            } else {
                self.state = ChannelState::Failed { error: None };
            }
            return Ok(());
        }
        let ChannelState::Sending { fragmenter, .. } = &mut self.state else {
            return Err(Error::not_ready());
        };
        let written = fragmenter.next(send_buffer, packet_buffer)?;
        if !written {
            return Err(Error::not_ready());
        }
        if fragmenter.is_done() {
            if fragmenter.header().channel_id() == BROADCAST_CHANNEL_ID {
                // This is a special case for `channel_allocation_response` which is the only
                // message sent through Channel (by `device::ChannelOpen`) but does not
                // wait for ACK because as it is sent on broadcast channel.
                self.state = ChannelState::Idle;
            } else {
                self.sync.send_finish();
            }
        }
        Ok(())
    }

    fn packet_out_ready(&self) -> bool {
        if self.send_ack.is_some() {
            return true;
        }
        match &self.state {
            ChannelState::Sending { fragmenter, .. } => !fragmenter.is_done(),
            ChannelState::SendingError { .. } => true,
            _ => false,
        }
    }

    fn message_in(&mut self, plaintext_len: usize, send_buffer: &mut [u8]) -> Result<()> {
        if !self.message_in_ready() {
            return Err(Error::not_ready());
        }
        let encrypted_len = plaintext_len + TAG_LEN;
        if send_buffer.len() < encrypted_len {
            return Err(Error::insufficient_buffer());
        }
        self.noise()?.encrypt(send_buffer, plaintext_len)?;
        let header = Header::new_encrypted(self.channel_id, &send_buffer[..encrypted_len])?;
        self.raw_in(header, send_buffer)
    }

    fn message_in_ready(&self) -> bool {
        matches!(self.state, ChannelState::Idle)
    }

    fn message_out<'a>(&mut self, receive_buffer: &'a mut [u8]) -> Result<(u8, u16, &'a [u8])> {
        let (header, len) = self.raw_out(receive_buffer)?;
        let receive_buffer = &mut receive_buffer[..len];

        if !header.is_encrypted() {
            log::error!(
                "[{}] Invalid message type, expecting EncryptedTransport.",
                self.channel_id
            );
            return Err(Error::malformed_data());
        }

        let receive_buffer = match self.noise()?.decrypt(receive_buffer) {
            Ok(plaintext_len) => &receive_buffer[..plaintext_len],
            Err(e) => {
                log::error!(
                    "[{}] Decryption failed, sending DECRYPTION_FAILED.",
                    self.channel_id
                );
                self.send_error(TransportError::DecryptionFailed); // TODO host only?
                return Err(e);
            }
        };
        if receive_buffer.len() < APP_HEADER_LEN {
            log::error!("[{}] Incoming message too short.", self.channel_id);
            // fails on the next two lines
        }
        let (session_id, rest) = receive_buffer
            .split_first()
            .ok_or_else(Error::malformed_data)?;
        let (message_type, rest) = parse_u16(rest)?;
        Ok((*session_id, message_type, rest))
    }

    fn message_out_ready(&self) -> bool {
        match &self.state {
            ChannelState::Receiving { reassembler } => reassembler.is_done(),
            _ => false,
        }
    }

    fn message_retransmit(&mut self) -> Result<()> {
        let ChannelState::Sending { fragmenter, retry } = &mut self.state else {
            log::warn!("[{}] Nothing to retransmit.", self.channel_id);
            return Ok(());
        };
        log::debug!("[{}] Retransmitting message.", self.channel_id);
        fragmenter.reset();
        *retry = retry.saturating_add(1);
        Ok(())
    }
}

/// Returns how many milliseconds to wait for an ACK for a given retransmission attempt.
/// First timeout (0th retry) is after 200ms till ~3.52s.
///
/// Taken from the original micropython implementation - not part of the specification,
/// you are free to use different function. It is recommended to measure the duration between
/// sending last packet and receiving an ACK ("ack_latency") and add it to this number.
pub fn retransmit_after_ms(retry: u8) -> u32 {
    const MAX_RETRANSMISSION_COUNT: u8 = 50;
    let retry: u32 = retry.min(MAX_RETRANSMISSION_COUNT).into();

    let res = 10300 - 1010000 / retry.saturating_add(100);
    res
}
