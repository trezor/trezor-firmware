use heapless;

use crate::{
    Backend, ChannelIO, Device, Error,
    alternating_bit::SyncBits,
    channel::{
        ChannelState, Nonce, PRIVKEY_LEN, PacketInResult, PairingState, noise::NoiseHandshake,
    },
    credential::CredentialVerifier,
    error::TransportError,
    fragment::{Fragmenter, Reassembler},
    header::{
        BROADCAST_CHANNEL_ID, HandshakeMessage, Header, MAX_CHANNEL_ID, MIN_CHANNEL_ID,
        channel_id_valid, parse_cb_channel,
    },
    util::prepare_zeroed,
};

use core::{
    marker::PhantomData,
    sync::atomic::{AtomicU16, Ordering},
};

// Must fit any of:
// - device_properties + overhead
// - 2 DH keys + 2 AEAD tags (2*32+2*16=96) + overhead
// - DH key + credential + 2 AEAD tags + overhead
const INTERNAL_BUFFER_LEN: usize = 192;
// As long as `packet_out` is called soon after `packet_in` there shouldn't be an accumulation
// of outgoing messages. However there still can be >1 during normal operation, e.g. when we're
// responding to PING at the same time the application requests sending an error.
const BROADCAST_OUTGOING_QUEUE_LEN: usize = 8;
// "?##" + Failure message type + msg_size + msg_data (code = "Failure_InvalidProtocol")
const CODEC_V1_RESPONSE: &[u8] = b"?##\x00\x03\x00\x00\x00\x02\x08\x11";

pub type Channel<B> = super::Channel<Device, B>;

/// Maps packets to channels. Handles broadcast channel messages, notably channel allocation.
/// Every packet interface on the device needs to have one Mux. Event loop should pass every
/// incoming packet to [`Mux::packet_in`] in order to determine what to do with it.
/// Single packet only. Does not keep track of opened channels.
pub struct Mux<B> {
    outgoing: heapless::Deque<MuxOutgoing, BROADCAST_OUTGOING_QUEUE_LEN>,
    new_channel: Option<Nonce>,
    _phantom: PhantomData<B>,
}

enum MuxOutgoing {
    Error(u16, TransportError),
    Pong(Nonce),
    CodecV1Response,
}

impl MuxOutgoing {
    pub fn to_str(&self) -> &'static str {
        match self {
            Self::Error(_, _) => "transport_error",
            Self::Pong(_) => "pong",
            Self::CodecV1Response => "codec_v1_response",
        }
    }
}

impl<B> Mux<B>
where
    B: Backend,
{
    pub const fn new() -> Self {
        Self {
            outgoing: heapless::Deque::new(),
            new_channel: None,
            _phantom: PhantomData,
        }
    }

    /// Create new [`ChannelOpen`] when channel allocation request is pending.
    pub fn channel_alloc<C>(
        &mut self,
        channel_id: u16,
        cred_verif: C,
    ) -> Result<ChannelOpen<C, B>, Error>
    where
        C: CredentialVerifier,
    {
        if !channel_id_valid(channel_id) || channel_id == BROADCAST_CHANNEL_ID {
            return Err(Error::unexpected_input());
        }
        let Some(nonce) = self.new_channel.take() else {
            return Err(Error::not_ready());
        };
        ChannelOpen::<C, B>::new(channel_id, nonce, cred_verif)
    }

    /// Returns `true` if there is channel allocation request pending.
    pub fn channel_alloc_ready(&self) -> bool {
        self.new_channel.is_some()
    }

    /// Enqueue `TransportError::TransportBusy` for given channel id. Event loop should call this whenever it
    /// gets packet for existing channel but cannot currently process it, for example because there is no
    /// available receive buffer. Host is supposed to try again later.
    pub fn send_transport_busy(&mut self, channel_id: u16) -> Result<(), Error> {
        self.enqueue(MuxOutgoing::Error(
            channel_id,
            TransportError::TransportBusy,
        ))
    }

    /// Enqueue TransportError::UnallocatedChannel for given channel id. Event loop should call this
    /// method whenever it gets [`PacketInResult::Route`] result for a channel that does not exist (anymore).
    pub fn send_unallocated_channel(&mut self, channel_id: u16) -> Result<(), Error> {
        self.enqueue(MuxOutgoing::Error(
            channel_id,
            TransportError::UnallocatedChannel,
        ))
    }

    fn enqueue(&mut self, outgoing: MuxOutgoing) -> Result<(), Error> {
        self.outgoing.push_back(outgoing).map_err(|o| {
            log::warn!(
                "Broadcast channel outgoing queue full, dropped {}.",
                o.to_str()
            );
            Error::not_ready()
        })
    }

    // Returns true if allocation request has been received.
    fn handle_broadcast(&mut self, packet: &[u8]) -> Result<bool, Error> {
        let (header, payload) = Reassembler::<Device>::single_inplace(packet)?;
        match header {
            Header::Ping if payload.len() == Nonce::LEN => {
                let (nonce, _rest) = Nonce::parse(payload)?;
                self.enqueue(MuxOutgoing::Pong(nonce)).map(|_| false)
            }
            Header::ChannelAllocationRequest if payload.len() == Nonce::LEN => {
                let (nonce, _rest) = Nonce::parse(payload)?;
                if self.new_channel.is_some() {
                    log::warn!("Dropping previous channel allocation request.");
                }
                self.new_channel = Some(nonce);
                Ok(true)
            }
            // No Header::TransportError for broadcast.
            _ => {
                log::debug!(
                    "Broadcast channel: ignoring packet with control byte {}.",
                    packet[0]
                );
                Err(Error::malformed_data())
            }
        }
    }

    fn handle_v1(&mut self, packet: &[u8]) -> PacketInResult {
        match Header::<Device>::parse(packet) {
            Ok((
                Header::CodecV1Request {
                    is_continuation: false,
                },
                _,
            )) => {
                let res = self
                    .enqueue(MuxOutgoing::CodecV1Response)
                    .map(|_| PacketInResult::accept(false));
                return PacketInResult::from_result(res);
            }
            Ok((Header::CodecV1Request { .. }, _)) => {
                log::debug!("Ignoring v1 continuation.");
            }
            _ => {
                log::error!("Malformed v1 packet.");
            }
        };
        PacketInResult::ignore(Error::malformed_data())
    }
}

impl<B> Default for Mux<B>
where
    B: Backend,
{
    fn default() -> Self {
        Self::new()
    }
}

impl<B> ChannelIO for Mux<B>
where
    B: Backend,
{
    fn packet_in(&mut self, packet_buffer: &[u8], _receive_buffer: &mut [u8]) -> PacketInResult {
        let Ok((cb, channel_id, _rest)) = parse_cb_channel(packet_buffer) else {
            // parse_cb_channel already writes to log
            return PacketInResult::ignore(Error::malformed_data());
        };
        if cb.is_codec_v1() {
            return self.handle_v1(packet_buffer);
        }
        if !channel_id_valid(channel_id) {
            log::warn!("Invalid channel id {}.", channel_id);
            return PacketInResult::ignore(Error::malformed_data());
        }
        if channel_id != BROADCAST_CHANNEL_ID {
            return PacketInResult::route(channel_id);
        }
        PacketInResult::from_result(self.handle_broadcast(packet_buffer).map(|is_allocation| {
            if is_allocation {
                PacketInResult::channel_allocation()
            } else {
                PacketInResult::accept(false)
            }
        }))
    }

    fn packet_in_ready(&self) -> bool {
        !self.outgoing.is_full()
    }

    fn packet_out(&mut self, packet_buffer: &mut [u8], _send_buffer: &[u8]) -> Result<(), Error> {
        let op = self.outgoing.pop_front().ok_or_else(Error::not_ready)?;
        let sb = SyncBits::new();
        match op {
            MuxOutgoing::Error(channel_id, transport_error) => Fragmenter::<Device>::single(
                Header::new_error(channel_id)?,
                sb,
                &[u8::from(transport_error)],
                packet_buffer,
            ),
            MuxOutgoing::Pong(nonce) => Fragmenter::<Device>::single(
                Header::new_pong(),
                sb,
                nonce.as_slice(),
                packet_buffer,
            ),
            MuxOutgoing::CodecV1Response => {
                let (response, zeros) = packet_buffer
                    .split_at_mut_checked(CODEC_V1_RESPONSE.len())
                    .ok_or_else(Error::insufficient_buffer)?;
                response.copy_from_slice(CODEC_V1_RESPONSE);
                zeros.fill(0);
                Ok(())
            }
        }
    }

    fn packet_out_ready(&self) -> bool {
        !self.outgoing.is_empty()
    }

    fn message_in(&mut self, _plaintext_len: usize, _send_buffer: &mut [u8]) -> Result<(), Error> {
        Ok(())
    }

    fn message_in_ready(&self) -> bool {
        false
    }

    fn message_out<'a>(
        &mut self,
        receive_buffer: &'a mut [u8],
    ) -> Result<(u8, u16, &'a [u8]), Error> {
        Ok((0, 0, &receive_buffer[..0]))
    }

    fn message_out_ready(&self) -> bool {
        false
    }

    fn message_retransmit(&mut self) -> Result<(), Error> {
        Ok(())
    }
}

#[derive(Copy, Clone)]
enum HandshakeState {
    SendingChannelResponse,
    StaticKeyRequired { try_to_unlock: bool },
    SendingInitiationResponse,
    SendingCompletionResponse { pairing_state: PairingState },
    SendingDeviceLocked,
    Failed,
}

/// Channel in the handshake phase. Perform [`ChannelIO`] with empty messages until
/// [`ChannelOpen::handshake_done`] is true, then call [`ChannelOpen::complete`].
/// Please note that this object also handles sending ChannelAllocationResponse
/// which is a broadcast message, which are normally handled by [`Mux`].
pub struct ChannelOpen<C: CredentialVerifier, B: Backend> {
    channel: Channel<B>,
    state: HandshakeState,
    noise: NoiseHandshake<Device, B>,
    internal_buffer: heapless::Vec<u8, INTERNAL_BUFFER_LEN>,
    cred_verif: C,
}

impl<C: CredentialVerifier, B: Backend> ChannelOpen<C, B> {
    fn new(channel_id: u16, nonce: Nonce, cred_verif: C) -> Result<Self, Error> {
        let mut internal_buffer = heapless::Vec::new();
        internal_buffer
            .extend_from_slice(nonce.as_slice())
            .map_err(|_| Error::insufficient_buffer())?;
        internal_buffer
            .extend_from_slice(&channel_id.to_be_bytes())
            .map_err(|_| Error::insufficient_buffer())?;
        internal_buffer
            .extend_from_slice(cred_verif.device_properties())
            .map_err(|_| Error::insufficient_buffer())?;

        // Sending `channel_allocation_response` on broadcast channel.
        let mut channel = Channel::new(channel_id);
        channel.raw_in(
            Header::new_channel_response(&internal_buffer)?,
            &internal_buffer,
        )?;
        Ok(Self {
            channel,
            state: HandshakeState::SendingChannelResponse,
            noise: NoiseHandshake::prepare_responder(cred_verif.device_properties()),
            internal_buffer,
            cred_verif,
        })
    }

    fn incoming_internal(&mut self) -> Result<(), Error> {
        let (header, len) = self.channel.raw_out(&self.internal_buffer)?;
        self.internal_buffer.truncate(len);

        match (self.state, header.handshake_phase()) {
            (HandshakeState::SendingChannelResponse, Some(HandshakeMessage::InitiationRequest)) => {
                let try_to_unlock = self.noise.read_initiation_request(&self.internal_buffer)?;
                self.state = HandshakeState::StaticKeyRequired { try_to_unlock };
            }
            (
                HandshakeState::SendingInitiationResponse,
                Some(HandshakeMessage::CompletionRequest),
            ) => {
                let pairing_state = self.send_completion_response()?;
                self.state = HandshakeState::SendingCompletionResponse { pairing_state };
            }
            _ => {
                log::error!("[{}] Unexpected handshake state.", self.channel_id());
                return Err(Error::unexpected_input());
            }
        }
        Ok(())
    }

    fn send_initiation_response(
        &mut self,
        static_privkey: &[u8; PRIVKEY_LEN],
    ) -> Result<(), Error> {
        prepare_zeroed(&mut self.internal_buffer);
        let msg = self
            .noise
            .write_initiation_response(static_privkey, &mut self.internal_buffer)?;
        let header = Header::new_handshake(
            self.channel.channel_id,
            HandshakeMessage::InitiationResponse,
            msg,
        )?;
        self.channel.raw_in(header, msg)?;
        let len = msg.len();
        self.internal_buffer.truncate(len);
        Ok(())
    }

    fn send_completion_response(&mut self) -> Result<PairingState, Error> {
        let payload = self.internal_buffer.clone();
        prepare_zeroed(&mut self.internal_buffer);
        let (nc, ps, msg) = self.noise.write_completion_response(
            &payload,
            &self.cred_verif,
            &mut self.internal_buffer,
        )?;
        self.channel.noise = Some(nc);
        let header = Header::new_handshake(
            self.channel.channel_id,
            HandshakeMessage::CompletionResponse,
            msg,
        )?;
        self.channel.raw_in(header, msg)?;
        let len = msg.len();
        self.internal_buffer.truncate(len);
        Ok(ps)
    }

    pub fn pairing_state(&self) -> Option<PairingState> {
        match self.state {
            HandshakeState::SendingCompletionResponse { pairing_state } => Some(pairing_state),
            _ => None,
        }
    }

    /// True if handshake finished and [`ChannelOpen::complete()`] can be called.
    pub fn handshake_done(&self) -> bool {
        // Done only after peer acknowledges completion response.
        matches!(self.state, HandshakeState::SendingCompletionResponse { .. })
            && matches!(self.channel.state, ChannelState::Idle)
    }

    /// True if the handshake failed and the object should be discarded.
    pub fn handshake_failed(&self) -> bool {
        matches!(self.state, HandshakeState::Failed)
            || matches!(self.channel.state, ChannelState::Failed(_))
    }

    /// True if the handshake is waiting for device static key to be supplied using
    /// [`ChannelOpen::set_static_key()`]. If the key is not available, handshake should be
    /// aborted using [`ChannelOpen::send_device_locked()`].
    pub fn static_key_required(&self) -> bool {
        matches!(self.state, HandshakeState::StaticKeyRequired { .. })
    }

    /// Finish the handshake and transition into the pairing/credential/appdata phase.
    ///
    /// Please note that the returned [`Channel`] is in the [Pairing phase] (state `TP0`). The peers
    /// must exchange protobuf messages as described in the [Pairing phase] and [Credential phase]
    /// section of THP spec. Only after `ThpMessageType_ThpEndResponse` is sent from the device to
    /// the host can regular application messages be transported. The library does not track whether
    /// the channel is in the pairing, credential, or application transport phase and it is the
    /// responsibility of the application to separate these message contexts.
    ///
    /// [Pairing phase]: https://docs.trezor.io/trezor-firmware/common/thp/specification.html#pairing-phase
    /// [Credential phase]: https://docs.trezor.io/trezor-firmware/common/thp/specification.html#credential-phase
    pub fn complete(self) -> Result<Channel<B>, Error> {
        if self.channel.noise.is_none() {
            return Err(Error::unexpected_input());
        }
        log::debug!("Handshake complete.");
        Ok(match self.state {
            HandshakeState::SendingCompletionResponse { .. } => self.channel,
            _ => return Err(Error::unexpected_input()),
        })
    }

    pub fn channel_id(&self) -> u16 {
        self.channel.channel_id
    }

    pub fn sending_retry(&self) -> Option<u8> {
        self.channel.sending_retry()
    }

    /// Notify host that handshake cannot proceed because device static key is not available.
    pub fn send_device_locked(&mut self) -> Result<(), Error> {
        if !self.static_key_required() {
            return Err(Error::not_ready());
        }
        let header = Header::new_error(self.channel.channel_id)?;
        self.internal_buffer.clear();
        let _ = self
            .internal_buffer
            .push(TransportError::DeviceLocked.into());
        self.channel.raw_in(header, &self.internal_buffer)?;
        self.state = HandshakeState::SendingDeviceLocked;
        Ok(())
    }

    /// Set static private key to be used for handshake. The key is not stored and can be
    /// disposed of after returning from this function.
    pub fn set_static_key(&mut self, static_privkey: &[u8; PRIVKEY_LEN]) -> Result<(), Error> {
        if !self.static_key_required() {
            return Err(Error::not_ready());
        }
        self.send_initiation_response(static_privkey)?;
        self.state = HandshakeState::SendingInitiationResponse;
        Ok(())
    }
}

impl<C, B> ChannelIO for ChannelOpen<C, B>
where
    C: CredentialVerifier,
    B: Backend,
{
    fn packet_in(&mut self, packet_buffer: &[u8], _receive_buffer: &mut [u8]) -> PacketInResult {
        let res = self
            .channel
            .packet_in(packet_buffer, &mut self.internal_buffer);
        if let PacketInResult::EnlargeBuffer { buffer_size, .. } = res {
            log::error!(
                "[{}] Payload length {} exceeds handshake limit.",
                self.channel_id(),
                buffer_size
            );
            // Possibly damaged length field, ignore continuations.
            self.channel.state = ChannelState::Idle;
            return PacketInResult::ignore(Error::malformed_data());
        }
        if res.got_ack() {
            if matches!(self.state, HandshakeState::SendingDeviceLocked) {
                self.state = HandshakeState::Failed;
                return res;
            }
            prepare_zeroed(&mut self.internal_buffer);
        }
        if res.got_message() {
            let handled = self.incoming_internal();
            if let Err(e) = handled {
                if e == Error::InvalidChecksum {
                    return PacketInResult::ignore(e);
                } else {
                    self.state = HandshakeState::Failed;
                    return PacketInResult::fail(e);
                }
            }
            if let HandshakeState::StaticKeyRequired { try_to_unlock } = self.state {
                return PacketInResult::HandshakeKeyRequired { try_to_unlock };
            }
        }
        res
    }

    fn packet_out(&mut self, packet_buffer: &mut [u8], _send_buffer: &[u8]) -> Result<(), Error> {
        self.channel
            .packet_out(packet_buffer, &self.internal_buffer)?;
        // Do not wait for ack - `channel_allocation_response` is sent over broadcast channel.
        if matches!(self.state, HandshakeState::SendingChannelResponse)
            && matches!(self.channel.state, ChannelState::Idle)
        {
            prepare_zeroed(&mut self.internal_buffer);
        }
        Ok(())
    }

    fn packet_out_ready(&self) -> bool {
        self.channel.packet_out_ready()
    }

    fn message_in(&mut self, _plaintext_len: usize, _send_buffer: &mut [u8]) -> Result<(), Error> {
        Ok(())
    }

    fn message_in_ready(&self) -> bool {
        !(self.handshake_done() || self.handshake_failed())
    }

    fn message_out<'a>(
        &mut self,
        receive_buffer: &'a mut [u8],
    ) -> Result<(u8, u16, &'a [u8]), Error> {
        Ok((0, 0, &receive_buffer[..0]))
    }

    fn message_out_ready(&self) -> bool {
        self.channel.message_out_ready()
    }

    fn message_retransmit(&mut self) -> Result<(), Error> {
        self.channel.message_retransmit()
    }
}

/// Helper for assigning consecutive channel IDs.
pub struct ChannelIdAllocator {
    // Next value. Not guaranteed to be valid channel id, these are skipped
    // in `ChannelIdAllocator::get()` until a valid one is found.
    counter: AtomicU16,
}

impl ChannelIdAllocator {
    /// Use random starting id to avoid giving out the number of channels allocated since boot.
    pub fn new_random<B: Backend>() -> Self {
        let mut bytes = [0u8, 0u8];
        B::random_bytes(&mut bytes);
        Self::new_from(u16::from_be_bytes(bytes))
    }

    /// Use fixed starting id, mainly useful for tests.
    /// Please note [`ChannelIdAllocator::get()`] skips invalid values so the first result
    /// is not necessarily the argument passed to this constructor.
    pub const fn new_from(init_val: u16) -> Self {
        Self {
            counter: AtomicU16::new(init_val),
        }
    }

    /// Get next ID. Wraps around to `MIN_CHANNEL_ID`.
    /// If the caller has multiple channels it needs to check whether the returned
    /// ID is not currently in use.
    pub fn get(&self) -> u16 {
        loop {
            let channel_id = self.counter.fetch_add(1, Ordering::Relaxed);
            if (MIN_CHANNEL_ID..=MAX_CHANNEL_ID).contains(&channel_id) {
                return channel_id;
            }
        }
    }
}
