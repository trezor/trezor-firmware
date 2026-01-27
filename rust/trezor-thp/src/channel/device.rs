use heapless;

use crate::{
    Backend, Channel, ChannelIO, Device, Error,
    channel::{Nonce, PacketInResult, PacketState, PairingState, noise::NoiseHandshake},
    credential::CredentialVerifier,
    fragment::Reassembler,
    header::{BROADCAST_CHANNEL_ID, HandshakeMessage, Header},
};

// muxer
// incoming traffic only?
// can tell you which channel is this packet for
// can allocate new channels
// sends TRANSPORT_BUSY, UNALLOCATED_CHANNEL, DEVICE_LOCKED, somebody must send DECRYPTION_FAILED still
// use_std blocking io impl

// Must fit any of:
// - device_properties + overhead
// - 2 DH keys + 2 AEAD tags (2*32+2*16=96) + overhead
// - DH key + credential + 2 AEAD tags + overhead
const INTERNAL_BUFFER_LEN: usize = 192;
const MESSAGE_TYPE_END_RESPONSE: u16 = 1019; // ThpMessageType_ThpEndResponse

#[derive(Copy, Clone)]
enum DeviceHandshakeState {
    SentChannelResponse,
    SentInitiationResponse,
    SentCompletionResponse(PairingState),
    Failed,
}

// XXX get device properties
pub struct ChannelOpen<C: CredentialVerifier, B: Backend> {
    channel: Channel<Device, B>,
    state: DeviceHandshakeState,
    noise: Option<NoiseHandshake<Device, B>>,
    internal_buffer: heapless::Vec<u8, INTERNAL_BUFFER_LEN>,
    cred_verif: C,
}

impl<C: CredentialVerifier, B: Backend> ChannelOpen<C, B> {
    pub fn new(
        channel_request_packet: &[u8],
        channel_id: u16,
        device_properties: &[u8],
        cred_verif: C,
    ) -> Result<Self, Error> {
        let mut incoming_payload = [0u8; 64];
        let (header, nonce) =
            Reassembler::<Device>::single(channel_request_packet, &mut incoming_payload)?;
        if !header.is_channel_allocation_request() || nonce.len() != Nonce::LEN {
            return Err(Error::malformed_data());
        }
        let mut internal_buffer = heapless::Vec::new();
        internal_buffer
            .extend_from_slice(nonce)
            .map_err(|_| Error::insufficient_buffer())?;
        internal_buffer
            .extend_from_slice(&channel_id.to_be_bytes())
            .map_err(|_| Error::insufficient_buffer())?;
        internal_buffer
            .extend_from_slice(device_properties)
            .map_err(|_| Error::insufficient_buffer())?;

        let mut channel = Channel::new(BROADCAST_CHANNEL_ID);
        channel.raw_in(
            Header::new_channel_response(&internal_buffer),
            &internal_buffer,
        )?;
        channel.channel_id = channel_id; // TODO document
        Ok(Self {
            channel,
            state: DeviceHandshakeState::SentChannelResponse,
            noise: None,
            internal_buffer,
            cred_verif,
        })
    }

    pub fn is_broadcast(&self) -> bool {
        self.channel.is_broadcast()
    }

    fn incoming_internal(&mut self) -> Result<(), Error> {
        let (header, len) = self.channel.raw_out(&self.internal_buffer)?;
        self.internal_buffer.truncate(len);

        match (self.state, header.handshake_phase()) {
            (
                DeviceHandshakeState::SentChannelResponse,
                Some(HandshakeMessage::InitiationRequest),
            ) => {
                self.start_handshake()?;
                self.state = DeviceHandshakeState::SentInitiationResponse;
            }
            (
                DeviceHandshakeState::SentInitiationResponse,
                Some(HandshakeMessage::CompletionRequest),
            ) => {
                let ps = self.continue_handshake()?;
                self.state = DeviceHandshakeState::SentCompletionResponse(ps); // FIXME
            }
            _ => {
                log::error!("[{}] Unexpected handshake state.", self.channel.channel_id);
                return Err(Error::unexpected_input());
            }
        }
        Ok(())
    }

    fn start_handshake(&mut self) -> Result<(), Error> {
        let payload = &self.internal_buffer.clone();
        self.zero_internal_buffer();
        let (hss, msg) = NoiseHandshake::<Device, B>::initiation_response(
            &[0u8; 32],
            payload,
            &[], /*device_properties*/
            &mut self.internal_buffer,
        )?;
        let header = Header::new_handshake(
            self.channel.channel_id,
            HandshakeMessage::InitiationResponse,
            msg,
        );
        self.noise = Some(hss);
        self.channel.raw_in(header, msg)?;
        let len = msg.len();
        self.internal_buffer.truncate(len);
        Ok(())
    }

    fn continue_handshake(&mut self) -> Result<PairingState, Error> {
        let payload = &self.internal_buffer.clone();
        self.zero_internal_buffer();
        let (nc, msg) = self.noise.as_mut().unwrap().completion_response(
            payload,
            &self.cred_verif,
            &mut self.internal_buffer,
        )?;
        self.channel.noise = Some(nc);
        self.noise = None;
        let header = Header::new_handshake(
            self.channel.channel_id,
            HandshakeMessage::CompletionResponse,
            msg,
        );
        self.channel.raw_in(header, msg)?;
        let len = msg.len();
        self.internal_buffer.truncate(len);
        Ok(PairingState::Unpaired /*FIXME */)
    }

    fn zero_internal_buffer(&mut self) {
        self.internal_buffer.clear();
        self.internal_buffer
            .resize(self.internal_buffer.capacity(), 0u8)
            .unwrap();
    }

    /// True if handshake finished and [`ChannelOpen::complete()`] can be called.
    pub fn handshake_done(&self) -> bool {
        matches!(self.state, DeviceHandshakeState::SentCompletionResponse(_))
    }

    /// True if the handshake failed and the object should be discarded.
    pub fn handshake_failed(&self) -> bool {
        matches!(self.state, DeviceHandshakeState::Failed)
    }

    /// Transition into the pairing phase.
    pub fn complete(self) -> Result<ChannelPairing<B>, Error> {
        if self.is_broadcast() || self.channel.noise.is_none() {
            return Err(Error::unexpected_input());
        }
        // TODO maybe check if channel idle?
        log::debug!("Handshake complete.");
        Ok(match self.state {
            DeviceHandshakeState::SentCompletionResponse(ps) => ChannelPairing {
                channel: self.channel,
                pairing_state: ps,
                is_finished: false,
            },
            _ => return Err(Error::unexpected_input()),
        })
    }
}

impl<C, B> ChannelIO for ChannelOpen<C, B>
where
    C: CredentialVerifier,
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
                self.state = DeviceHandshakeState::Failed;
            }
            handled?;
        }
        Ok(res)
    }

    fn packet_out(&mut self, packet_buffer: &mut [u8], _send_buffer: &[u8]) -> Result<(), Error> {
        self.channel
            .packet_out(packet_buffer, &self.internal_buffer)?;
        if matches!(self.state, DeviceHandshakeState::SentChannelResponse)
            && matches!(self.channel.packet_state, PacketState::Idle)
        {
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

    fn message_retransmit(&mut self) -> Result<(), Error> {
        self.channel.message_retransmit()
    }
}

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
