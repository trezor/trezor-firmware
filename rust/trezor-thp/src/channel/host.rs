use heapless;

use crate::{
    Backend, Channel, ChannelIO, Error, Host,
    alternating_bit::SyncBits,
    channel::{ChannelState, Nonce, PacketInResult, PairingState, noise::NoiseHandshake},
    credential::CredentialStore,
    fragment::{Fragmenter, Reassembler},
    header::{
        BROADCAST_CHANNEL_ID, HandshakeMessage, Header, channel_id_valid, parse_cb_channel,
        parse_u16,
    },
    util::prepare_zeroed,
};

use core::marker::PhantomData;

// Must fit any of:
// - device_properties + overhead
// - 2 DH keys + 2 AEAD tags (2*32+2*16=96) + overhead
// - DH key + credential + 2 AEAD tags + overhead
const INTERNAL_BUFFER_LEN: usize = 192;
const MAX_DEVICE_PROPERTIES_LEN: usize = 128;
const MESSAGE_TYPE_END_RESPONSE: u16 = 1019; // ThpMessageType_ThpEndResponse

enum AllocationState {
    None,
    SendingRequest {
        try_to_unlock: bool,
    },
    /// `HH0`.
    SentRequest {
        try_to_unlock: bool,
        nonce: Nonce,
    },
    ReceivingResponse {
        try_to_unlock: bool,
        nonce: Nonce,
        reassembler: Reassembler<Host>,
    },
    ReceivedId {
        try_to_unlock: bool,
        channel_id: u16,
    },
}

/// Handles broadcast channel messages, notably channel allocation requests.
/// Because host often only needs a single channel, you can throw away the Mux
/// after allocating one, if you don't need the keep-alive functionality.
pub struct Mux<C, B> {
    cred_store: C,
    internal_buffer: heapless::Vec<u8, MAX_DEVICE_PROPERTIES_LEN>,
    channel_allocation: AllocationState,
    ping: Option<(bool, Nonce)>,
    _phantom: PhantomData<B>,
}

impl<C, B> Mux<C, B>
where
    C: CredentialStore,
    B: Backend,
{
    pub fn new(cred_store: C) -> Self {
        let mut internal_buffer = heapless::Vec::new();
        prepare_zeroed(&mut internal_buffer);
        Self {
            cred_store,
            internal_buffer,
            channel_allocation: AllocationState::None,
            ping: None,
            _phantom: PhantomData,
        }
    }

    /// Enqueue a keep-alive message.
    pub fn ping(&mut self) {
        if self.ping.is_some() {
            log::warn!("Dropping previous ping attempt.");
        }
        self.ping = Some((false, Nonce::random::<B>()));
    }

    /// Enqueue channel allocation request.
    pub fn request_channel(&mut self, try_to_unlock: bool) {
        self.channel_allocation = AllocationState::SendingRequest { try_to_unlock };
    }

    /// Create new [`ChannelOpen`] after channel allocation response was received.
    pub fn channel_alloc(&mut self) -> Result<ChannelOpen<C, B>, Error> {
        let AllocationState::ReceivedId {
            try_to_unlock,
            channel_id,
        } = self.channel_allocation
        else {
            return Err(Error::not_ready());
        };
        let ch = ChannelOpen::new(
            channel_id,
            self.cred_store.clone(),
            &self.internal_buffer,
            try_to_unlock,
        )?;
        self.channel_allocation = AllocationState::None;
        prepare_zeroed(&mut self.internal_buffer);
        Ok(ch)
    }

    /// True if [`Mux::channel_alloc`] can be called.
    pub fn channel_alloc_ready(&self) -> bool {
        matches!(self.channel_allocation, AllocationState::ReceivedId { .. })
    }

    /// Same as [`Mux::channel_alloc`] but destroys the [`Mux`],
    /// like `complete()` does for other types.
    pub fn complete(mut self) -> Result<ChannelOpen<C, B>, Error> {
        self.channel_alloc()
    }

    fn handle_broadcast(&mut self, packet: &[u8]) -> Result<PacketInResult, Error> {
        let (header, _rest) = Header::<Host>::parse(packet)?;
        match header {
            Header::Pong => {
                let (_header, payload) = Reassembler::<Host>::single_inplace(packet)?;
                let (nonce, _rest) = Nonce::parse(payload)?;
                if Some((true, nonce)) != self.ping {
                    log::warn!("Ignoring PONG with invalid nonce.");
                    return Err(Error::malformed_data());
                }
                self.ping = None;
                Ok(PacketInResult::pong())
            }
            Header::ChannelAllocationResponse { .. } => {
                let (try_to_unlock, nonce) = match self.channel_allocation {
                    AllocationState::SentRequest {
                        try_to_unlock,
                        nonce,
                        ..
                    } => (try_to_unlock, nonce),
                    AllocationState::ReceivingResponse {
                        try_to_unlock,
                        nonce,
                        ..
                    } => (try_to_unlock, nonce),
                    _ => return Err(Error::malformed_data()),
                };
                self.internal_buffer.fill(0u8);
                let reassembler = Reassembler::<Host>::new(packet, &mut self.internal_buffer)?;
                self.channel_allocation = AllocationState::ReceivingResponse {
                    try_to_unlock,
                    nonce,
                    reassembler,
                };
                self.handle_allocation_response()
            }
            Header::Continuation {
                channel_id: BROADCAST_CHANNEL_ID,
            } => {
                let AllocationState::ReceivingResponse { reassembler, .. } =
                    &mut self.channel_allocation
                else {
                    return Err(Error::malformed_data());
                };
                reassembler.update(packet, &mut self.internal_buffer)?;
                self.handle_allocation_response()
            }
            // No Header::TransportError for broadcast channel.
            _ => {
                log::debug!(
                    "Broadcast channel: ignoring packet with control byte {}.",
                    packet[0]
                );
                Err(Error::malformed_data())
            }
        }
    }

    fn handle_allocation_response(&mut self) -> Result<PacketInResult, Error> {
        let AllocationState::ReceivingResponse {
            try_to_unlock,
            nonce,
            reassembler,
        } = &mut self.channel_allocation
        else {
            return Ok(PacketInResult::accept(false));
        };
        if !reassembler.is_done() {
            return Ok(PacketInResult::accept(false));
        }
        let len = reassembler.verify(self.internal_buffer.as_slice())?;
        let payload = &self.internal_buffer[..len];

        let (received_nonce, payload) = Nonce::parse(payload)?;
        if received_nonce != *nonce {
            log::warn!("Received non matching channel request nonce.");
            return Ok(PacketInResult::accept(false));
        };
        let (channel_id, device_properties) = parse_u16(payload)?;
        let device_properties_len = device_properties.len();
        // Shift internal buffer to only contain device_properties.
        self.internal_buffer.copy_within(Nonce::LEN + 2..len, 0);
        self.internal_buffer.truncate(device_properties_len);
        self.channel_allocation = AllocationState::ReceivedId {
            try_to_unlock: *try_to_unlock,
            channel_id,
        };
        log::debug!("Got channel id {}.", channel_id);
        Ok(PacketInResult::channel_allocation(channel_id))
    }
}

impl<C, B> ChannelIO for Mux<C, B>
where
    C: CredentialStore,
    B: Backend,
{
    fn packet_in(&mut self, packet_buffer: &[u8], _receive_buffer: &mut [u8]) -> PacketInResult {
        let Ok((_cb, channel_id, _rest)) = parse_cb_channel(packet_buffer) else {
            // parse_cb_channel already writes to log
            return PacketInResult::ignore(Error::malformed_data());
        };
        if !channel_id_valid(channel_id) {
            log::warn!("Invalid channel id {}.", channel_id);
            return PacketInResult::ignore(Error::malformed_data());
        }
        if channel_id != BROADCAST_CHANNEL_ID {
            return PacketInResult::route(channel_id);
        }
        PacketInResult::from_result(self.handle_broadcast(packet_buffer))
    }

    fn packet_in_ready(&self) -> bool {
        true
    }

    fn packet_out(&mut self, packet_buffer: &mut [u8], _send_buffer: &[u8]) -> Result<(), Error> {
        if let AllocationState::SendingRequest { try_to_unlock } = self.channel_allocation {
            let nonce = Nonce::random::<B>();
            Fragmenter::<Host>::single(
                Header::new_channel_request(),
                SyncBits::new(),
                nonce.as_slice(),
                packet_buffer,
            )?;
            self.channel_allocation = AllocationState::SentRequest {
                try_to_unlock,
                nonce,
            };
        } else if let Some((false, _)) = self.ping {
            let nonce = Nonce::random::<B>();
            Fragmenter::<Host>::single(
                Header::new_ping(),
                SyncBits::new(),
                nonce.as_slice(),
                packet_buffer,
            )?;
            self.ping = Some((true, nonce));
        } else {
            return Err(Error::not_ready());
        }
        Ok(())
    }

    fn packet_out_ready(&self) -> bool {
        let send_ping = matches!(self.ping, Some((false, _)));
        let send_channel_allocation = matches!(
            self.channel_allocation,
            AllocationState::SendingRequest { .. }
        );
        send_ping || send_channel_allocation
    }

    fn message_in(&mut self, _plaintext_len: usize, _send_buffer: &mut [u8]) -> Result<(), Error> {
        Ok(())
    }

    fn message_in_ready(&self) -> bool {
        true
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
    /// `HH1`.
    SentInitiationRequest,
    /// `HH2`.
    SentCompletionRequest,
    /// `HP0`.
    Finished(PairingState),
    /// Handshake cannot be finished.
    Failed,
}

/// Open a [`Channel`] from the host side.
///
/// - start by calling [`Mux::request_channel`]
/// - perform [`ChannelIO`] with empty messages until [`PacketInResult::ChannelAllocation`] is returned
/// - calling [`Mux::channel_alloc`] to obtain [`ChannelOpen`]
/// - perform [`ChannelIO`] with empty messages until [`ChannelOpen::handshake_done`]
/// - call [`ChannelOpen::complete`] to obtain [`ChannelPairing`]
/// - perform [`ChannelIO`] until [`ChannelPairing::pairing_done`]
/// - call [`ChannelPairing::complete`] to get established [`Channel`]
pub struct ChannelOpen<C: CredentialStore, B: Backend> {
    channel: Channel<Host, B>,
    state: HandshakeState,
    noise: NoiseHandshake<Host, B>,
    internal_buffer: heapless::Vec<u8, INTERNAL_BUFFER_LEN>,
    device_properties: heapless::Vec<u8, MAX_DEVICE_PROPERTIES_LEN>,
    cred_store: C,
}

impl<C: CredentialStore, B: Backend> ChannelOpen<C, B> {
    fn new(
        channel_id: u16,
        cred_store: C,
        device_properties: &[u8],
        try_to_unlock: bool,
    ) -> Result<Self, Error> {
        let device_properties = heapless::Vec::from_slice(device_properties)
            .map_err(|_| Error::insufficient_buffer())?;

        let mut internal_buffer = heapless::Vec::new();
        prepare_zeroed(&mut internal_buffer);
        let (hss, msg) = NoiseHandshake::initiation_request(
            &device_properties,
            try_to_unlock,
            &mut internal_buffer,
        )?;
        let header = Header::new_handshake(channel_id, HandshakeMessage::InitiationRequest, msg)?;
        let mut channel = Channel::new(channel_id);
        channel.raw_in(header, msg)?;
        let len = msg.len();
        internal_buffer.truncate(len);
        let res = Self {
            channel,
            state: HandshakeState::SentInitiationRequest,
            noise: hss,
            internal_buffer,
            device_properties,
            cred_store,
        };
        Ok(res)
    }

    fn incoming_internal(&mut self) -> Result<(), Error> {
        let (header, len) = self.channel.raw_out(&self.internal_buffer)?;
        self.internal_buffer.truncate(len);

        match (self.state, header.handshake_phase()) {
            (HandshakeState::SentInitiationRequest, Some(HandshakeMessage::InitiationResponse)) => {
                self.continue_handshake()?;
                self.state = HandshakeState::SentCompletionRequest;
            }
            (HandshakeState::SentCompletionRequest, Some(HandshakeMessage::CompletionResponse)) => {
                let device_state = self.finish_handshake()?;
                self.state = HandshakeState::Finished(device_state);
            }
            _ => {
                log::error!("Unexpected handshake state.");
                return Err(Error::unexpected_input());
            }
        }
        Ok(())
    }

    fn continue_handshake(&mut self) -> Result<(), Error> {
        let payload_len = self.internal_buffer.len();
        // Buffer used both for input and output - pad with zeros.
        self.internal_buffer
            .resize(self.internal_buffer.capacity(), 0u8)
            .unwrap();
        let (nc, msg) = self.noise.completion_request(
            &mut self.cred_store,
            &mut self.internal_buffer,
            payload_len,
        )?;
        self.channel.noise = Some(nc);
        let header = Header::new_handshake(
            self.channel.channel_id,
            HandshakeMessage::CompletionRequest,
            msg,
        )?;
        self.channel.raw_in(header, msg)?;
        let len = msg.len();
        self.internal_buffer.truncate(len);
        Ok(())
    }

    fn finish_handshake(&mut self) -> Result<PairingState, Error> {
        let payload = &mut self.internal_buffer;
        let len = self.channel.noise()?.decrypt(payload.as_mut_slice())?;
        payload.truncate(len); // assumes tag at the end
        PairingState::try_from(payload.as_slice())
    }

    pub fn device_properties(&self) -> &[u8] {
        self.device_properties.as_slice()
    }

    /// True if handshake finished and [`ChannelOpen::complete()`] can be called.
    pub fn handshake_done(&self) -> bool {
        matches!(self.state, HandshakeState::Finished(_))
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
            HandshakeState::Finished(ps) => ChannelPairing {
                channel: self.channel,
                device_properties: self.device_properties,
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
    C: CredentialStore,
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
            return PacketInResult::ignore(Error::MalformedData);
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
            .packet_out(packet_buffer, &self.internal_buffer)
    }

    fn packet_out_ready(&self) -> bool {
        self.channel.packet_out_ready()
    }

    fn message_in(&mut self, _plaintext_len: usize, _send_buffer: &mut [u8]) -> Result<(), Error> {
        // Messages from application are ignored during the handshake.
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
/// Application must use this object to exchange protobuf messages as described in
/// the [Pairing phase] and [Credential phase] section of THP spec. After
/// `ThpMessageType_ThpEndResponse` is received, call [`ChannelPairing::complete`]
/// to obtain a [`Channel`].
///
/// Corresponds to states `HP0`..`HC2` in the spec.
///
/// [Pairing phase]: https://docs.trezor.io/trezor-firmware/common/thp/specification.html#pairing-phase
/// [Credential phase]: https://docs.trezor.io/trezor-firmware/common/thp/specification.html#credential-phase
pub struct ChannelPairing<B: Backend> {
    channel: Channel<Host, B>,
    device_properties: heapless::Vec<u8, MAX_DEVICE_PROPERTIES_LEN>,
    pairing_state: PairingState,
    is_finished: bool, // true after Trezor sends ThpEndResponse, should we block sending messages afterwards?
}

impl<B: Backend> ChannelPairing<B> {
    pub fn pairing_done(&self) -> bool {
        self.is_finished
    }

    pub fn device_properties(&self) -> &[u8] {
        self.device_properties.as_slice()
    }

    pub fn pairing_state(&self) -> PairingState {
        self.pairing_state
    }

    pub fn complete(self) -> Result<Channel<Host, B>, Error> {
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
        if message_type == MESSAGE_TYPE_END_RESPONSE {
            self.is_finished = true;
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
