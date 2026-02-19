use heapless;

use crate::{
    Backend, Channel, ChannelIO, Device, Error,
    alternating_bit::SyncBits,
    channel::{ChannelState, Nonce, PacketInResult, PairingState, noise::NoiseHandshake},
    credential::CredentialVerifier,
    error::TransportError,
    fragment::{Fragmenter, Reassembler},
    header::{
        BROADCAST_CHANNEL_ID, HandshakeMessage, Header, MAX_CHANNEL_ID, MIN_CHANNEL_ID,
        channel_id_valid, parse_cb_channel,
    },
    util::prepare_zeroed,
};

use core::marker::PhantomData;

// Must fit any of:
// - device_properties + overhead
// - 2 DH keys + 2 AEAD tags (2*32+2*16=96) + overhead
// - DH key + credential + 2 AEAD tags + overhead
const INTERNAL_BUFFER_LEN: usize = 192;
const MESSAGE_TYPE_END_RESPONSE: u16 = 1019; // ThpMessageType_ThpEndResponse
// As long as `packet_out` is called soon after `packet_in` there shouldn't be an accumulation
// of outgoing messages. However there still can be >1 during normal operation, e.g. when we're
// responding to PING at the same time the application requests sending an error.
const BROADCAST_OUTGOING_QUEUE_LEN: usize = 8;
// "?##" + Failure message type + msg_size + msg_data (code = "Failure_InvalidProtocol")
const CODEC_V1_RESPONSE: &[u8] = b"?##\x00\x03\x00\x00\x00\x14\x08\x11";

/// Maps packets to channels. Handles broadcast channel messages, notably channel allocation.
/// Every packet interface on the device needs to have one Mux. Event loop should pass every
/// incoming packet to [`Mux::packet_in`] in order to determine what to do with it.
/// Single packet only. Does not keep track of opened channels.
pub struct Mux<C, B> {
    // is_locked: bool,
    next_channel_id: u16,
    cred_verif: C,
    outgoing: heapless::Deque<MuxOutgoing, BROADCAST_OUTGOING_QUEUE_LEN>,
    new_channel: Option<(u16, Nonce)>,
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

impl<C, B> Mux<C, B>
where
    C: CredentialVerifier,
    B: Backend,
{
    pub fn new(cred_verif: C) -> Self {
        // Use random starting id to avoid giving out the number of channels allocated since boot.
        let next_channel_id = random_channel_id::<B>();
        Self {
            next_channel_id,
            cred_verif,
            outgoing: heapless::Deque::new(),
            new_channel: None,
            _phantom: PhantomData,
        }
    }

    /// Create new [`ChannelOpen`] when channel allocation request is pending.
    pub fn channel_alloc(&mut self) -> Result<ChannelOpen<C, B>, Error> {
        let Some((channel_id, nonce)) = self.new_channel.take() else {
            return Err(Error::not_ready());
        };
        ChannelOpen::<C, B>::new(channel_id, nonce, self.cred_verif.clone())
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
        ))?;
        Ok(())
    }

    /// Enqueue TransportError::UnallocatedChannel for given channel id. Event loop should call this
    /// method whenever it gets [`PacketInResult::Route`] result for a channel that does not exist (anymore).
    pub fn send_unallocated_channel(&mut self, channel_id: u16) -> Result<(), Error> {
        self.enqueue(MuxOutgoing::Error(
            channel_id,
            TransportError::UnallocatedChannel,
        ))?;
        Ok(())
    }

    fn enqueue(&mut self, outgoing: MuxOutgoing) -> Result<(), Error> {
        self.outgoing.push_back(outgoing).map_err(|o| {
            log::warn!(
                "Broadcast channel outgoing queue full, dropped {}.",
                o.to_str()
            );
            Error::not_ready()
        })?;
        Ok(())
    }

    fn handle_broadcast(&mut self, packet: &[u8]) -> Result<Option<u16>, Error> {
        let (header, payload) = Reassembler::<Device>::single_inplace(packet)?;
        match header {
            Header::Ping if payload.len() == Nonce::LEN => {
                let (nonce, _rest) = Nonce::parse(payload).unwrap();
                self.enqueue(MuxOutgoing::Pong(nonce)).map(|_| None)
            }
            Header::ChannelAllocationRequest if payload.len() == Nonce::LEN => {
                let (nonce, _rest) = Nonce::parse(payload)?;
                let channel_id = self.next_channel_id;
                self.next_channel_id += 1;
                if self.next_channel_id > MAX_CHANNEL_ID {
                    log::debug!("Channel id max value reached, wrapping around.");
                    self.next_channel_id = MIN_CHANNEL_ID;
                }
                if self.new_channel.is_some() {
                    log::warn!("Dropping previous channel allocation request.");
                }
                self.new_channel = Some((channel_id, nonce));
                Ok(Some(channel_id))
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

    #[cfg(test)]
    pub(crate) fn set_next_channel_id(&mut self, channel_id: u16) {
        assert!(channel_id_valid(channel_id));
        self.next_channel_id = channel_id;
    }
}

impl<C, B> ChannelIO for Mux<C, B>
where
    C: CredentialVerifier,
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
        PacketInResult::from_result(self.handle_broadcast(packet_buffer).map(|r| {
            r.map_or_else(
                || PacketInResult::accept(false),
                PacketInResult::channel_allocation,
            )
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
    SentChannelResponse,
    SentInitiationResponse,
    SentCompletionResponse(PairingState),
    Failed,
}

/// Channel in the handshake phase. Perform [`ChannelIO`] with empty messages until
/// [`ChannelOpen::handshake_done`] is true, then call [`ChannelOpen::complete`].
/// Please note that this object also handles sending ChannelAllocationResponse
/// which is a broadcast message, which are normally handled by [`Mux`].
pub struct ChannelOpen<C: CredentialVerifier, B: Backend> {
    channel: Channel<Device, B>,
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
            state: HandshakeState::SentChannelResponse,
            noise: NoiseHandshake::prepare_responder(
                cred_verif.static_privkey(),
                cred_verif.device_properties(),
            ),
            internal_buffer,
            cred_verif,
        })
    }

    fn incoming_internal(&mut self) -> Result<(), Error> {
        let (header, len) = self.channel.raw_out(&self.internal_buffer)?;
        self.internal_buffer.truncate(len);

        match (self.state, header.handshake_phase()) {
            (HandshakeState::SentChannelResponse, Some(HandshakeMessage::InitiationRequest)) => {
                self.start_handshake()?;
                self.state = HandshakeState::SentInitiationResponse;
            }
            (HandshakeState::SentInitiationResponse, Some(HandshakeMessage::CompletionRequest)) => {
                let pairing_state = self.continue_handshake()?;
                self.state = HandshakeState::SentCompletionResponse(pairing_state);
            }
            _ => {
                log::error!("[{}] Unexpected handshake state.", self.channel_id());
                return Err(Error::unexpected_input());
            }
        }
        Ok(())
    }

    fn start_handshake(&mut self) -> Result<(), Error> {
        let payload = self.internal_buffer.clone();
        prepare_zeroed(&mut self.internal_buffer);
        let (_try_to_unlock, msg) = self
            .noise
            .initiation_response(&payload, &mut self.internal_buffer)?;
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

    fn continue_handshake(&mut self) -> Result<PairingState, Error> {
        let payload = self.internal_buffer.clone();
        prepare_zeroed(&mut self.internal_buffer);
        let (nc, ps, msg) = self.noise.completion_response(
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

    /// True if handshake finished and [`ChannelOpen::complete()`] can be called.
    pub fn handshake_done(&self) -> bool {
        matches!(self.state, HandshakeState::SentCompletionResponse(_))
    }

    /// True if the handshake failed and the object should be discarded.
    pub fn handshake_failed(&self) -> bool {
        matches!(self.state, HandshakeState::Failed)
    }

    /// Transition into the pairing phase.
    pub fn complete(self) -> Result<ChannelPairing<B>, Error> {
        if self.channel.noise.is_none() {
            return Err(Error::unexpected_input());
        }
        log::debug!("Handshake complete.");
        Ok(match self.state {
            HandshakeState::SentCompletionResponse(ps) => ChannelPairing {
                channel: self.channel,
                pairing_state: ps,
                is_finished: false,
            },
            _ => return Err(Error::unexpected_input()),
        })
    }

    pub fn channel_id(&self) -> u16 {
        self.channel.channel_id
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
            prepare_zeroed(&mut self.internal_buffer);
        }
        if res.got_message() {
            let handled = self.incoming_internal();
            if let Err(e) = handled {
                if e != Error::InvalidChecksum {
                    self.state = HandshakeState::Failed;
                    return PacketInResult::fail(e);
                }
            }
        }
        res
    }

    fn packet_out(&mut self, packet_buffer: &mut [u8], _send_buffer: &[u8]) -> Result<(), Error> {
        self.channel
            .packet_out(packet_buffer, &self.internal_buffer)?;
        // Do not wait for ack - `channel_allocation_response` is sent over broadcast channel.
        if matches!(self.state, HandshakeState::SentChannelResponse)
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

/// Channel in the pairing or credentials phase.
///
/// Device must use this object to exchange protobuf messages as described in
/// the [Pairing phase] and [Credential phase] section of THP spec. After
/// `ThpMessageType_ThpEndResponse` is sent, call [`ChannelPairing::complete`]
/// to obtain a [`Channel`].
///
/// Corresponds to states `TP0`..`TC1` in the spec.
///
/// [Pairing phase]: https://docs.trezor.io/trezor-firmware/common/thp/specification.html#pairing-phase
/// [Credential phase]: https://docs.trezor.io/trezor-firmware/common/thp/specification.html#credential-phase
pub struct ChannelPairing<B: Backend> {
    channel: Channel<Device, B>,
    pairing_state: PairingState,
    is_finished: bool, // true after we send ThpEndResponse, should we block sending messages afterwards?
}

impl<B: Backend> ChannelPairing<B> {
    pub fn pairing_done(&self) -> bool {
        self.is_finished
    }

    pub fn pairing_state(&self) -> PairingState {
        self.pairing_state
    }

    pub fn complete(self) -> Result<Channel<Device, B>, Error> {
        if !self.is_finished {
            return Err(Error::unexpected_input());
        }
        log::debug!("Pairing and credentials complete, begin application level transport.");
        Ok(self.channel)
    }
}

impl<B: Backend> ChannelIO for ChannelPairing<B> {
    fn packet_in(&mut self, packet_buffer: &[u8], receive_buffer: &mut [u8]) -> PacketInResult {
        self.channel.packet_in(packet_buffer, receive_buffer)
    }

    fn packet_out(&mut self, packet_buffer: &mut [u8], send_buffer: &[u8]) -> Result<(), Error> {
        self.channel.packet_out(packet_buffer, send_buffer)
    }

    fn packet_out_ready(&self) -> bool {
        self.channel.packet_out_ready()
    }

    fn message_in(&mut self, plaintext_len: usize, send_buffer: &mut [u8]) -> Result<(), Error> {
        if send_buffer.len().min(plaintext_len) >= 3 {
            let message_type = u16::from_be_bytes([send_buffer[1], send_buffer[2]]);
            if message_type == MESSAGE_TYPE_END_RESPONSE {
                self.is_finished = true;
            }
        }
        self.channel.message_in(plaintext_len, send_buffer)
    }

    fn message_in_ready(&self) -> bool {
        self.channel.message_in_ready()
    }

    fn message_out<'a>(
        &mut self,
        receive_buffer: &'a mut [u8],
    ) -> Result<(u8, u16, &'a [u8]), Error> {
        let (sid, message_type, message) = self.channel.message_out(receive_buffer)?;
        if sid != 0 {
            log::error!("Invalid session id in pairing phase.");
            return Err(Error::malformed_data());
        }
        Ok((0, message_type, message))
    }

    fn message_out_ready(&self) -> bool {
        self.channel.message_out_ready()
    }

    fn message_retransmit(&mut self) -> Result<(), Error> {
        self.channel.message_retransmit()
    }
}

fn random_channel_id<B: Backend>() -> u16 {
    let mut bytes = [0u8, 0u8];
    for _i in 0..16 {
        B::random_bytes(&mut bytes);
        let channel_id = u16::from_be_bytes(bytes);
        if channel_id_valid(channel_id) && channel_id != BROADCAST_CHANNEL_ID {
            return channel_id;
        }
    }
    panic!("Cannot generate random channel id.");
}
