pub mod host;
mod noise;

use crate::{
    Error, Role,
    alternating_bit::{ChannelSync, SyncBits},
    error::TransportError,
    fragment::{Fragmenter, Reassembler},
    header::{BROADCAST_CHANNEL_ID, Header, NONCE_LEN, parse_cb_channel},
};

pub use noise::Backend;
use noise::{HANDSHAKE_HASH_LEN, NoiseCiphers, TAG_LEN};

const APP_HEADER_LEN: usize = 3; // session id (1) + message type (2)

/// Sent by device after successful handshake to indicate whether pairing is required.
#[repr(u8)]
#[derive(Copy, Clone)]
pub enum PairingState {
    Unpaired = 0,
    Paired = 1,
    PairedAutoconnect = 2,
}

type Nonce = [u8; NONCE_LEN];

impl PairingState {
    pub fn from(bytes: &[u8]) -> Option<Self> {
        Some(match bytes {
            [0] => Self::Unpaired,
            [1] => Self::Paired,
            [2] => Self::PairedAutoconnect,
            _ => return None,
        })
    }

    pub fn is_paired(&self) -> bool {
        !matches!(self, Self::Unpaired)
    }
}

/// Is the channel currently sending or receiving a message?
enum PacketState<R: Role> {
    /// Ready to send or receive.
    Idle,
    /// In the process of sending a message, or waiting for ACK.
    Sending(Fragmenter<R>),
    /// In the process of receiving a message, or waiting for the consumer to pick up
    /// an assembled message.
    Receiving(Reassembler<R>),
}

/// THP channel with established secure layer.
///
/// There is no constructor, to obtain a channel please use [`host::ChannelOpen`]
/// or `device::ChannelOpen`.
/// For actually sending and receiving messages please see [`ChannelIO`].
pub struct Channel<R: Role, B: Backend> {
    channel_id: u16,
    sync: ChannelSync,
    noise: Option<NoiseCiphers<B>>,
    send_ack: Option<SyncBits>,
    packet_state: PacketState<R>,
}

impl<R: Role, B: Backend> Channel<R, B> {
    fn new(channel_id: u16) -> Self {
        Self {
            channel_id,
            sync: ChannelSync::new(),
            noise: None,
            send_ack: None,
            packet_state: PacketState::Idle,
        }
    }

    fn noise(&mut self) -> &mut NoiseCiphers<B> {
        self.noise.as_mut().unwrap()
    }

    fn is_broadcast(&self) -> bool {
        self.channel_id == BROADCAST_CHANNEL_ID
    }

    pub fn channel_id(&self) -> u16 {
        self.channel_id
    }

    pub fn handshake_hash(&self) -> &[u8; HANDSHAKE_HASH_LEN] {
        self.noise.as_ref().unwrap().handshake_hash()
    }

    fn raw_in(&mut self, header: Header<R>, send_buffer: &[u8]) -> Result<(), Error> {
        let PacketState::Idle = self.packet_state else {
            return Err(Error::NotReady);
        };
        let sb = if self.is_broadcast() {
            SyncBits::new()
        } else {
            self.sync.send_start().ok_or(Error::NotReady)?
        };
        let frag = Fragmenter::new(header, sb, send_buffer)?;
        self.packet_state = PacketState::Sending(frag);
        Ok(())
    }

    fn raw_out(&mut self, receive_buffer: &[u8]) -> Result<(Header<R>, usize), Error> {
        let has_cid = !self.is_broadcast();
        let PacketState::Receiving(r) = &mut self.packet_state else {
            return Err(Error::NotReady);
        };
        if !r.is_done() {
            return Err(Error::NotReady);
        }
        let len = match r.verify(receive_buffer) {
            Ok(len) => len,
            Err(e) => {
                log::warn!(
                    "[{}] Reassembled message with invalid digest.",
                    self.channel_id
                );
                return Err(e);
            }
        };
        // TODO possiby handle TransportError?
        if has_cid {
            // Will be unset by `message_out()` if authenticated decryption fails.
            self.send_ack = Some(self.sync.receive_acknowledge());
        }
        let header = r.header();
        self.packet_state = PacketState::Idle;
        Ok((header, len))
    }
}

/// Whether channel state changed after calling [`ChannelIO::packet_in`].
pub struct PacketInResult {
    ack_received: bool,
    message_ready: bool,
    // what about "channel has become invalid after this packet"?
}

impl PacketInResult {
    const fn new(ack_received: bool, message_ready: bool) -> Self {
        Self {
            ack_received,
            message_ready,
        }
    }

    pub const fn nothing() -> Result<Self, Error> {
        Ok(Self::new(false, false))
    }

    pub const fn ack() -> Result<Self, Error> {
        Ok(Self::new(true, false))
    }

    pub const fn message() -> Result<Self, Error> {
        Ok(Self::new(false, true))
    }

    /// True if the received packet was valid ACK.
    pub const fn got_ack(&self) -> bool {
        self.ack_received
    }

    /// True if the received packet was the last fragment of incoming message.
    /// Event loop should call [`ChannelIO::message_out`]. The message is
    /// not guaranteed to be valid.
    pub const fn got_message(&self) -> bool {
        self.message_ready
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
    fn packet_in(
        &mut self,
        packet_buffer: &[u8],
        receive_buffer: &mut [u8],
    ) -> Result<PacketInResult, Error>;

    /// Is channel ready to accept incoming packet?
    ///
    /// Only provided for completenes as the channel is always ready to drop unexpected packets.
    fn packet_in_ready(&self) -> bool {
        true
    }

    /// Write outgoing packet to `packet_buffer`. Returns [`Error::NotReady`] if there isn't one.
    fn packet_out(&mut self, packet_buffer: &mut [u8], send_buffer: &[u8]) -> Result<(), Error>;

    /// Is channel ready to send a packet?
    fn packet_out_ready(&self) -> bool;

    /// Submit prepared send buffer to encrypt and fragment into packets.
    ///
    /// The message including the application header (session id, message type) is passed in
    /// `send_buffer`, occupying first `plaintext_len` bytes. There must be at least 16 more
    /// bytes in the buffer for authentication tag.
    ///
    /// Instead of this function you can use [`Self::message_in_from`] to prepare the send
    /// buffer for you.
    ///
    /// Returns [`Error::NotReady`] if the channel hasn't finished sending the previous message
    /// (did not send all fragments or did not receive valid ACK), or if the channel is
    /// currently receiving.
    fn message_in(&mut self, plaintext_len: usize, send_buffer: &mut [u8]) -> Result<(), Error>;

    /// Is channel ready to send next message?
    ///
    /// After calling [`Self::message_in`] this method returns `false` until valid ACK is received
    /// from the other side.
    fn message_in_ready(&self) -> bool;

    /// Pick up reassembled and decrypted message. The channel will send ACK packet afterwards.
    ///
    /// Returns [`Error::NotReady`] if there is no reassembled message.
    ///
    /// Returns [`Error::InvalidDigest`] if message integrity or authenticity check failed.
    /// Usually the other side will retransmit the message.
    fn message_out<'a>(
        &mut self,
        receive_buffer: &'a mut [u8],
    ) -> Result<(u8, u16, &'a [u8]), Error>;

    /// Is there a reassembled incoming message ready?
    ///
    /// You can use [`PacketInResult::got_message`] instead of this method.
    ///
    /// Please note the incoming message may not be valid.
    fn message_out_ready(&self) -> bool; // unused

    /// Retransmit message previously submitted using [`Self::message_in`]. Does nothing if
    /// ACK was already received.
    fn message_retransmit(&mut self, send_buffer: &[u8]) -> Result<(), Error>;

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
    ) -> Result<(), Error> {
        if !self.message_in_ready() {
            return Err(Error::NotReady);
        }
        let plaintext_len = message.len() + APP_HEADER_LEN;
        if send_buffer.len() < plaintext_len {
            return Err(Error::InsufficientBuffer);
        }
        send_buffer[0] = session_id;
        send_buffer[1..3].copy_from_slice(&message_type.to_be_bytes());
        send_buffer[3..plaintext_len].copy_from_slice(message);
        self.message_in(plaintext_len, send_buffer)
    }
}

impl<R: Role, B: Backend> ChannelIO for Channel<R, B> {
    fn packet_in(
        &mut self,
        packet_buffer: &[u8],
        receive_buffer: &mut [u8],
    ) -> Result<PacketInResult, Error> {
        let (cb, channel_id, _rest) = parse_cb_channel(packet_buffer)?;
        if channel_id != self.channel_id {
            log::warn!(
                "[{}] Invalid channel {}, ignoring.",
                self.channel_id,
                channel_id
            );
            return PacketInResult::nothing();
        }
        let has_cid = !self.is_broadcast();
        if cb.is_ack() {
            if has_cid && matches!(self.packet_state, PacketState::Sending(_)) {
                // ignore ACKs on broadcast channel
                let sb = SyncBits::from(packet_buffer);
                self.sync.send_mark_delivered(sb);
                if self.sync.can_send() {
                    self.packet_state = PacketState::Idle;
                    return PacketInResult::ack();
                }
            }
            return PacketInResult::nothing();
        }

        let is_cont = cb.is_continuation();
        match &mut self.packet_state {
            PacketState::Receiving(_) | PacketState::Idle if !is_cont => {
                let sb = SyncBits::from(packet_buffer);
                if has_cid && !self.sync.receive_start(sb) {
                    // bad sync bit, drop this message and continuations
                    log::debug!("[{}] Bad sync bit, ignoring message.", self.channel_id);
                    self.packet_state = PacketState::Idle;
                    return PacketInResult::nothing();
                }
                receive_buffer.fill(0);
                let ra = Reassembler::new(packet_buffer, receive_buffer)?;
                self.packet_state = PacketState::Receiving(ra);
            }
            PacketState::Idle => return PacketInResult::nothing(), // ignore continuations
            PacketState::Receiving(r) => {
                r.update(packet_buffer, receive_buffer)?;
            }
            PacketState::Sending(_) => {
                // might possibly happen when we've sent an ACK and it got lost
                // we end up sending reply
                // while the other side is retransmitting
                // is this recoverable
                // TODO also handle TRANSPORT_BUSY
                return PacketInResult::nothing();
            }
        };

        match &self.packet_state {
            PacketState::Receiving(r) if r.is_done() => PacketInResult::message(),
            PacketState::Receiving(_) => PacketInResult::nothing(),
            _ => return Err(Error::UnexpectedInput),
        }
    }

    fn packet_out(&mut self, packet_buffer: &mut [u8], send_buffer: &[u8]) -> Result<(), Error> {
        // Send pending ACK.
        if let Some(sb) = self.send_ack.take() {
            let header = Header::<R>::new_ack(self.channel_id);
            Fragmenter::single(header, sb, &[], packet_buffer)?;
            return Ok(());
        }
        let PacketState::Sending(f) = &mut self.packet_state else {
            return Err(Error::NotReady);
        };
        let written = f.next(send_buffer, packet_buffer)?;
        if !written {
            return Err(Error::NotReady);
        }
        if f.is_done() {
            if self.is_broadcast() {
                // No ACKs without channel ID, assume delivered.
                self.packet_state = PacketState::Idle;
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
        match &self.packet_state {
            PacketState::Sending(f) => !f.is_done(),
            _ => false,
        }
    }

    fn message_in(&mut self, plaintext_len: usize, send_buffer: &mut [u8]) -> Result<(), Error> {
        if !self.message_in_ready() {
            return Err(Error::NotReady);
        }
        let encrypted_len = plaintext_len + TAG_LEN;
        if send_buffer.len() < encrypted_len {
            return Err(Error::InsufficientBuffer);
        }
        self.noise().encrypt(send_buffer, plaintext_len)?;
        let header = Header::new_encrypted(self.channel_id, &send_buffer[..encrypted_len]);
        self.raw_in(header, send_buffer)
    }

    fn message_in_ready(&self) -> bool {
        matches!(self.packet_state, PacketState::Idle)
    }

    fn message_out<'a>(
        &mut self,
        receive_buffer: &'a mut [u8],
    ) -> Result<(u8, u16, &'a [u8]), Error> {
        let (header, len) = self.raw_out(receive_buffer)?;
        let receive_buffer = &mut receive_buffer[..len];

        if header.is_error() {
            let b = receive_buffer.first().ok_or(Error::MalformedData)?;
            let e: TransportError = b.try_into()?;
            log::error!("[{}] Transport error: {}", self.channel_id, e as u8);
            return Err(Error::MalformedData); // FIXME propagate error
        } else if !header.is_encrypted() {
            log::error!(
                "[{}] Invalid message type, expecting EncryptedTransport.",
                self.channel_id
            );
            return Err(Error::MalformedData);
        }

        let receive_buffer = match self.noise().decrypt(receive_buffer) {
            Ok(plaintext_len) => &receive_buffer[..plaintext_len],
            Err(e) => {
                log::warn!("[{}] Decryption failed.", self.channel_id);
                // Cancel ACK (requested in `raw_out`), wait for retransmit.
                self.send_ack = None;
                return Err(e);
            }
        };
        if receive_buffer.len() < APP_HEADER_LEN {
            log::error!("[{}] Incoming message too short", self.channel_id);
        }
        let (session_id, rest) = receive_buffer.split_first().ok_or(Error::MalformedData)?;
        let (message_type, rest) = rest.split_first_chunk::<2>().ok_or(Error::MalformedData)?;
        let message_type = u16::from_be_bytes(*message_type);

        Ok((*session_id, message_type, rest))
    }

    fn message_out_ready(&self) -> bool {
        match &self.packet_state {
            PacketState::Receiving(r) => r.is_done(),
            _ => false,
        }
    }

    fn message_retransmit(&mut self, _send_buffer: &[u8]) -> Result<(), Error> {
        let PacketState::Sending(f) = &mut self.packet_state else {
            log::warn!("[{}] Nothing to retransmit.", self.channel_id);
            return Ok(());
        };
        log::debug!("[{}] Retransmitting message.", self.channel_id);
        f.reset();
        Ok(())
    }
}
