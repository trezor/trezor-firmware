use heapless;

use crate::{
    Backend, Channel, ChannelIO, Error, Host,
    channel::{Nonce, PacketInResult, PacketState, PairingState, noise::NoiseHandshake},
    credential::CredentialStore,
    error::TransportError,
    header::{BROADCAST_CHANNEL_ID, HandshakeMessage, Header, parse_u16},
};

// Must fit any of:
// - device_properties + overhead
// - 2 DH keys + 2 AEAD tags (2*32+2*16=96) + overhead
// - DH key + credential + 2 AEAD tags + overhead
const INTERNAL_BUFFER_LEN: usize = 192;
const MAX_DEVICE_PROPERTIES_LEN: usize = 128;
const MESSAGE_TYPE_END_RESPONSE: u16 = 1019; // ThpMessageType_ThpEndResponse

#[derive(Copy, Clone)]
enum HostHandshakeState {
    /// `HH0`.
    SentChannelRequest(Nonce),
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
/// - start by calling [`ChannelOpen::new`]
/// - perform [`ChannelIO`] with empty messages until [`ChannelOpen::handshake_done`]
/// - call [`ChannelOpen::complete`] to obtain [`ChannelPairing`]
/// - perform [`ChannelIO`] until [`ChannelPairing::pairing_done`]
/// - call [`ChannelPairing::complete`] to get established [`Channel`]
pub struct ChannelOpen<C: CredentialStore, B: Backend> {
    channel: Channel<Host, B>,
    state: HostHandshakeState,
    noise: Option<NoiseHandshake<Host, B>>,
    internal_buffer: heapless::Vec<u8, INTERNAL_BUFFER_LEN>,
    device_properties: heapless::Vec<u8, MAX_DEVICE_PROPERTIES_LEN>,
    cred_store: C,
    try_to_unlock: bool,
}

impl<C: CredentialStore, B: Backend> ChannelOpen<C, B> {
    pub fn new(try_to_unlock: bool, cred_store: C) -> Result<Self, Error> {
        let mut nonce = Nonce::default();
        B::random_bytes(&mut nonce);
        let internal_buffer = heapless::Vec::from_slice(&nonce).unwrap();
        let mut channel = Channel::new(BROADCAST_CHANNEL_ID);
        channel.raw_in(Header::new_channel_request(), &internal_buffer)?;
        let res = Self {
            channel,
            state: HostHandshakeState::SentChannelRequest(nonce),
            noise: None,
            internal_buffer,
            device_properties: heapless::Vec::new(),
            cred_store,
            try_to_unlock,
        };
        Ok(res)
    }

    pub fn is_broadcast(&self) -> bool {
        self.channel.is_broadcast()
    }

    fn incoming_internal(&mut self) -> Result<(), Error> {
        let (header, len) = self.channel.raw_out(&self.internal_buffer)?;
        self.internal_buffer.truncate(len);

        if header.is_error() {
            let b = self.internal_buffer.first().ok_or(Error::MalformedData)?;
            let e: TransportError = b.try_into()?;
            log::error!("[{}] Transport error: {}", self.channel.channel_id, e as u8);
            // TODO handle TransportError::Locked
        }

        match (self.state, header.handshake_phase()) {
            (HostHandshakeState::SentChannelRequest(nonce), _)
                if header.is_channel_allocation_response() =>
            {
                self.get_channel(&nonce)?;
                log::debug!("Got channel id {}.", self.channel.channel_id);
                self.start_handshake()?;
                self.state = HostHandshakeState::SentInitiationRequest;
            }
            (
                HostHandshakeState::SentInitiationRequest,
                Some(HandshakeMessage::InitiationResponse),
            ) => {
                self.continue_handshake()?;
                self.state = HostHandshakeState::SentCompletionRequest;
            }
            (
                HostHandshakeState::SentCompletionRequest,
                Some(HandshakeMessage::CompletionResponse),
            ) => {
                let device_state = self.finish_handshake()?;
                self.state = HostHandshakeState::Finished(device_state);
            }
            _ => {
                log::error!("Unexpected handshake state.");
                return Err(Error::UnexpectedInput);
            }
        }
        Ok(())
    }

    fn get_channel(&mut self, expected_nonce: &Nonce) -> Result<(), Error> {
        let Some((_nonce, payload)) = self
            .internal_buffer
            .as_slice()
            .split_at_checked(core::mem::size_of::<Nonce>())
            .filter(|(nonce, _payload)| nonce == expected_nonce)
        else {
            log::error!("Received invalid channel request nonce.");
            return Err(Error::MalformedData);
        };
        let (cid, device_properties) = parse_u16(payload)?;
        self.channel.channel_id = cid;
        self.device_properties =
            heapless::Vec::from_slice(device_properties).map_err(|_| Error::InsufficientBuffer)?;
        Ok(())
    }

    fn start_handshake(&mut self) -> Result<(), Error> {
        self.zero_internal_buffer();
        let (hss, msg) = NoiseHandshake::start_pairing(
            &self.device_properties,
            self.try_to_unlock,
            &mut self.internal_buffer,
        )?;
        let len = msg.len();
        self.internal_buffer.truncate(len);
        let header = Header::new_handshake(
            self.channel.channel_id,
            HandshakeMessage::InitiationRequest,
            &self.internal_buffer,
        );
        self.noise = Some(hss);
        self.channel.raw_in(header, &self.internal_buffer)
    }

    fn continue_handshake(&mut self) -> Result<(), Error> {
        let payload = &self.internal_buffer.clone();
        self.zero_internal_buffer();
        let (nc, msg) = self.noise.as_mut().unwrap().complete_pairing(
            payload,
            &mut self.cred_store,
            &mut self.internal_buffer,
        )?;
        self.channel.noise = Some(nc);
        self.noise = None;
        let len = msg.len();
        self.internal_buffer.truncate(len);
        let header = Header::new_handshake(
            self.channel.channel_id,
            HandshakeMessage::CompletionRequest,
            &self.internal_buffer,
        );

        self.channel.raw_in(header, &self.internal_buffer)
    }

    fn finish_handshake(&mut self) -> Result<PairingState, Error> {
        let mut payload = self.internal_buffer.clone();
        let len = self.channel.noise().decrypt(payload.as_mut_slice())?;
        payload.truncate(len); // assumes tag at the end
        PairingState::from(&payload).ok_or(Error::MalformedData)
    }

    fn zero_internal_buffer(&mut self) {
        self.internal_buffer.clear();
        self.internal_buffer
            .resize(self.internal_buffer.capacity(), 0u8)
            .unwrap();
    }

    /// True if handshake finished and [`ChannelOpen::complete()`] can be called.
    pub fn handshake_done(&self) -> bool {
        matches!(self.state, HostHandshakeState::Finished(_))
    }

    /// True if the handshake failed and the object should be discarded.
    pub fn handshake_failed(&self) -> bool {
        matches!(self.state, HostHandshakeState::Failed)
    }

    /// Transition into the pairing phase.
    pub fn complete(self) -> Result<ChannelPairing<B>, Error> {
        if self.is_broadcast() || self.channel.noise.is_none() {
            return Err(Error::UnexpectedInput);
        }
        log::debug!("Handshake complete.");
        Ok(match self.state {
            HostHandshakeState::Finished(ps) => ChannelPairing {
                channel: self.channel,
                device_properties: self.device_properties,
                pairing_state: ps,
                is_finished: false,
            },
            _ => return Err(Error::UnexpectedInput),
        })
    }
}

impl<C, B> ChannelIO for ChannelOpen<C, B>
where
    C: CredentialStore,
    B: Backend,
{
    fn packet_in(
        &mut self,
        packet_buffer: &[u8],
        _receive_buffer: &mut [u8],
    ) -> Result<PacketInResult, Error> {
        let res = self
            .channel
            .packet_in(packet_buffer, &mut self.internal_buffer)?;
        if res.got_ack() {
            self.zero_internal_buffer();
        }
        if res.got_message() {
            let handled = self.incoming_internal();
            if handled.is_err() {
                self.state = HostHandshakeState::Failed;
            }
            handled?;
        }
        Ok(res)
    }

    fn packet_out(&mut self, packet_buffer: &mut [u8], _send_buffer: &[u8]) -> Result<(), Error> {
        self.channel
            .packet_out(packet_buffer, &self.internal_buffer)?;

        if self.channel.is_broadcast() && matches!(self.channel.packet_state, PacketState::Idle) {
            // no ack/retransmits on broadcast
            self.zero_internal_buffer();
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

    fn message_retransmit(&mut self, send_buffer: &[u8]) -> Result<(), Error> {
        self.channel.message_retransmit(send_buffer)
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
/// [Credentail phase]: https://docs.trezor.io/trezor-firmware/common/thp/specification.html#credential-phase
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
            return Err(Error::UnexpectedInput);
        }
        log::debug!("Pairing and credentials complete, begin application level transport.");
        Ok(self.channel)
    }
}

impl<B: Backend> ChannelIO for ChannelPairing<B> {
    fn packet_in(
        &mut self,
        packet_buffer: &[u8],
        receive_buffer: &mut [u8],
    ) -> Result<PacketInResult, Error> {
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
            return Err(Error::MalformedData);
        }
        if message_type == MESSAGE_TYPE_END_RESPONSE {
            self.is_finished = true;
        }
        Ok((0, message_type, message))
    }

    fn message_out_ready(&self) -> bool {
        self.channel.message_out_ready()
    }

    fn message_retransmit(&mut self, send_buffer: &[u8]) -> Result<(), Error> {
        self.channel.message_retransmit(send_buffer)
    }
}
