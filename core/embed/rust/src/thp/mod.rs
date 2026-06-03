mod crypto;
pub mod micropython;
mod time;

use crate::{error::Error, micropython::obj::Obj, time::Instant};

use core::num::NonZeroU16;

use heapless::{
    deque::{Deque, DequeView},
    linear_map::{Entry, LinearMap, LinearMapView},
    Vec,
};
use spin::{Lazy, Mutex};

use trezor_thp::{
    channel::{
        device::{Channel, ChannelIdAllocator, ChannelOpen, Mux},
        PacketInResult, PairingState, Phase, MAX_CREDENTIAL_LEN, MAX_RETRANSMISSION_COUNT,
        PUBKEY_LEN,
    },
    control_byte::ControlByte,
    credential::CredentialVerifier,
    error::TransportError,
    ChannelIO, Error as ThpError,
};

use crypto::TrezorCrypto;
use time::{least_recently_used, ChannelTiming};

type TrezorMux = Mux<TrezorCrypto>;
type TrezorChannelOpen = ChannelOpen<TrezorCredentialVerifier, TrezorCrypto>;
type TrezorChannel = Channel<TrezorCrypto>;

type PubKey = [u8; PUBKEY_LEN];

#[cfg(not(feature = "ble"))]
const MAX_INTERFACES: usize = 1;
#[cfg(feature = "ble")]
const MAX_INTERFACES: usize = 2;

// Channel limits, shared across interfaces.
const MAX_CHANNELS_OPENING: usize = 4;
const MAX_CHANNELS_APPDATA: usize = 10;

const CANNOT_UNLOCK: Error = Error::ThpError(c"THP state locked");
const CHANNEL_NOT_FOUND: Error = Error::ThpError(c"Channel not found");
const INTERFACE_NOT_FOUND: Error = Error::ThpError(c"Invalid interface");

/// Global THP state.
/// Needs to be wrapped in a mutex because even without threads the compiler
/// cannot guarantee that borrowing rules are obeyed.
static THP_CONTEXT: Mutex<ThpContext> = Mutex::new(ThpContext::new());

/// Auxiliary THP state. Contains data that need to be accessed by
/// TrezorCredentialVerifier::verify while THP_CONTEXT is already locked
/// (host keys, credentials).
static THP_AUX: Mutex<Auxiliary> = Mutex::new(Auxiliary::new());

/// Next channel ID to be allocated. These are unique across interfaces.
static CHANNEL_ID_COUNTER: Lazy<ChannelIdAllocator> =
    Lazy::new(ChannelIdAllocator::new_random::<TrezorCrypto>);

/// State of channels and interfaces.
// Currently around 7KiB with 4/10 opening/appdata.
struct ThpContext {
    /// Muxes handles broadcast messages, channel allocation, CodecV1 responses.
    ifaces: LinearMap<u8, TrezorMux, MAX_INTERFACES>,
    /// Channels in the opening phase, with associated timing data, indexed by
    /// (iface_num, channel_id). Unlike application data channels,
    /// their messages are handled internally and not passed to python.
    /// Size note: these are larger than appdata channels due to the Noise
    /// handshake state and an internal buffer that needs to fit
    /// MAX_CREDENTIAL_LEN + 48 bytes.
    channel_opening: LinearMap<(u8, u16), (TrezorChannelOpen, ChannelTiming), MAX_CHANNELS_OPENING>,
    /// Channels in the pairing, credential, or encrypted transport phase.
    /// Maps `(iface_num, channel_id) -> (channel_data, timing_data)`.
    channel_appdata: LinearMap<(u8, u16), (TrezorChannel, ChannelTiming), MAX_CHANNELS_APPDATA>,
    /// Whenever a channel is closed during send/receive error, python needs to
    /// be notified in order to delete the associated sessions. This queue holds
    /// the IDs of such channels. Only channels in encrypted transport state are
    /// affected because other channels don't have sessions.
    channel_closed: Deque<(u8, u16), MAX_CHANNELS_APPDATA>,
    /// Sort of logical clock that is increased every time
    /// [`ChannelTiming::last_usage`] is increased.
    last_usage_counter: u32,
}

impl ThpContext {
    pub const fn new() -> Self {
        Self {
            ifaces: LinearMap::new(),
            channel_opening: LinearMap::new(),
            channel_appdata: LinearMap::new(),
            channel_closed: Deque::new(),
            last_usage_counter: 0,
        }
    }

    /// Create new initial interface context. Returns error when
    /// `device_properties` is longer than `MAX_DEVICE_PROPERTIES_LEN`.
    pub fn add_interface(&mut self, iface_num: u8, device_properties: &[u8]) -> Result<(), Error> {
        match self.ifaces.entry(iface_num) {
            Entry::Occupied(_) => {
                // already exists
            }
            Entry::Vacant(v) => {
                v.insert(TrezorMux::new(device_properties)?)
                    .map_err(|_| Error::ThpError(c"Too many interfaces"))?;
            }
        }
        Ok(())
    }

    /// Process a packet received by an interface. Returns [`TrezorInResult`]
    /// which indicates if anything else needs to be done with the packet.
    pub fn packet_in(
        &mut self,
        iface_num: u8,
        packet_buffer: &[u8],
        credential_fn: Obj,
    ) -> Result<TrezorInResult, Error> {
        let mux = self.ifaces.get_mut(&iface_num).ok_or(INTERFACE_NOT_FOUND)?;
        let pir = mux.packet_in(packet_buffer, &mut []);
        let res = match pir {
            PacketInResult::Accepted { .. } => TrezorInResult::None,
            PacketInResult::Ignored { .. } => TrezorInResult::None,
            PacketInResult::Route {
                channel_id,
                buffer_size,
            } => {
                if self.channel_opening.contains_key(&(iface_num, channel_id)) {
                    return self.packet_in_handshake(
                        iface_num,
                        channel_id,
                        packet_buffer,
                        credential_fn,
                    );
                }
                if !self.channel_appdata.contains_key(&(iface_num, channel_id)) {
                    log::debug!(
                        "[{:04x}] Received packet for unallocated channel.",
                        channel_id
                    );
                    // Only reply to initiation packets.
                    if packet_buffer
                        .first()
                        .and_then(|b| ControlByte::try_from(*b).ok())
                        .is_some_and(|cb| !cb.is_continuation())
                    {
                        mux.send_unallocated_channel(channel_id)?;
                    }
                    return Ok(TrezorInResult::None);
                }
                TrezorInResult::Route {
                    channel_id,
                    buffer_size,
                }
            }
            PacketInResult::ChannelAllocation => {
                self.packet_in_alloc(iface_num)?;
                return Ok(TrezorInResult::None);
            }
            _ => {
                return Err(Error::ThpError(c"Unexpected PacketInResult"));
            }
        };
        Ok(res)
    }

    /// Allocates a channel and starts the handshake process. Closes the oldest
    /// channel in handshake phase if needed.
    fn packet_in_alloc(&mut self, iface_num: u8) -> Result<(), Error> {
        let channel_id = self.get_channel_id();
        let mux = self.ifaces.get_mut(&iface_num).ok_or(INTERFACE_NOT_FOUND)?;
        let channel = mux.channel_alloc(
            channel_id,
            TrezorCredentialVerifier::new(iface_num, channel_id),
        )?;

        if let Some((ifn, cid)) = Self::lru_needs_closing(&self.channel_opening) {
            self.channel_close(ifn, cid);
        }
        Self::insert_channel(
            self.channel_opening.as_mut_view(),
            iface_num,
            channel_id,
            channel,
            ChannelTiming::new(Instant::now()),
        );
        self.channel_update_last_usage(channel_id);
        Ok(())
    }

    // Called by `packet_in` to process a packet for channel in the handshake phase.
    // Might invoke the python credential verification callback.
    fn packet_in_handshake(
        &mut self,
        iface_num: u8,
        channel_id: u16,
        packet_buffer: &[u8],
        credential_fn: Obj,
    ) -> Result<TrezorInResult, Error> {
        let (channel, timing) = self
            .channel_opening
            .get_mut(&(iface_num, channel_id))
            .ok_or(CHANNEL_NOT_FOUND)?;
        // Set all host keys aside so that TrezorCredentialVerifier can look up
        // peer key for channel replacement purposes. Does not work across interfaces.
        // As a possible optimization we can check packet's control byte and only do it
        // if it's HandshakeCompletionRequest.
        // Alternatively we can copy these to micropython before credential_fn is
        // called.
        {
            let mut aux = THP_AUX.try_lock().ok_or(CANNOT_UNLOCK)?;
            aux.host_keys_copy_from(iface_num, self.channel_appdata.as_view());
        };
        // Set credential verification callback here - we don't want to keep a
        // longer-lived reference as it could either keep the function alive
        // across session restart (if GC is aware of it), or we could end up
        // holding a reference to non-existent object (if GC is not aware of it).
        channel.credential_verifier().verify_fn = credential_fn;
        let pir = channel.packet_in(packet_buffer, &mut []);
        channel.credential_verifier().verify_fn = Obj::const_none();
        if pir.got_ack() {
            timing.read_ack(Instant::now());
        }
        if pir.got_message() && channel.sending_retry() == Some(0) {
            // Internal state machine accepted incoming message, and prepared outgoing one.
            // Update last_write as if message_in was called.
            timing.update_last_write(Instant::now());
        }
        let res = match pir {
            PacketInResult::Accepted { .. } => TrezorInResult::None,
            PacketInResult::Ignored { .. } => TrezorInResult::None,
            PacketInResult::Failed { .. } => {
                log::error!("[{:04x}] Handshake failed.", channel_id);
                self.channel_close(iface_num, channel_id);
                // micropython doesn't know about the channel, no point returning Failure
                return Ok(TrezorInResult::None);
            }
            PacketInResult::HandshakeKeyRequired { try_to_unlock } => {
                TrezorInResult::KeyRequired { try_to_unlock }
            }
            _ => {
                return Err(Error::ThpError(c"Unexpected PacketInResult"));
            }
        };
        if channel.handshake_done() {
            let (channel, timing) = unwrap!(self.channel_opening.remove(&(iface_num, channel_id)));
            let channel = channel.complete()?;

            if let Some((ifn, cid)) = Self::lru_needs_closing(&self.channel_appdata) {
                self.channel_close(ifn, cid);
            }
            Self::insert_channel(
                self.channel_appdata.as_mut_view(),
                iface_num,
                channel_id,
                channel,
                timing,
            );
            self.channel_update_last_usage(channel_id);
        }
        Ok(res)
    }

    /// Process a packet for channel in pairing+credential, or encrypted
    /// transport (appdata) phase - when `packet_in` returns
    /// `TrezorInResult::Route`. A receive buffer needs to be supplied by
    /// micropython caller.
    pub fn packet_in_channel(
        &mut self,
        iface_num: u8,
        channel_id: u16,
        packet_buffer: &[u8],
        receive_buffer: &mut [u8],
    ) -> Result<TrezorInResult, Error> {
        let (channel, timing) = self.lookup_channel_mut(iface_num, channel_id)?;
        let pir = channel.packet_in(packet_buffer, receive_buffer);
        let res = match pir {
            PacketInResult::Accepted {
                ack_received,
                message_ready,
                ..
            } => {
                if ack_received {
                    timing.read_ack(Instant::now());
                }
                match (message_ready, ack_received) {
                    (true, true) => TrezorInResult::MessageReadyAck,
                    (true, false) => TrezorInResult::MessageReady,
                    (false, true) => TrezorInResult::Ack,
                    _ => TrezorInResult::None,
                }
            }
            PacketInResult::Ignored { .. } => TrezorInResult::None,
            PacketInResult::Failed { .. } | PacketInResult::TransportError { .. } => {
                self.channel_close(iface_num, channel_id);
                TrezorInResult::Failed
            }
            _ => {
                return Err(Error::ThpError(c"Unexpected PacketInResult"));
            }
        };
        Ok(res)
    }

    /// Write outgoing packet for the broadcast channel or any channel in the
    /// handshake phase. Returns false if no such packet is ready to be
    /// sent.
    pub fn packet_out(&mut self, iface_num: u8, packet_buffer: &mut [u8]) -> Result<bool, Error> {
        let mux = self.ifaces.get_mut(&iface_num).ok_or(INTERFACE_NOT_FOUND)?;
        if mux.packet_out_ready() {
            mux.packet_out(packet_buffer, &[])?;
            return Ok(true);
        }
        let mut written = false;
        let mut failed = None;
        for ((ifn, _cid), (channel, _t)) in self.channel_opening.iter_mut() {
            if *ifn != iface_num {
                continue;
            }
            if channel.packet_out_ready() {
                channel.packet_out(packet_buffer, &[])?;
                written = true;
                failed = channel.handshake_failed().then_some(channel.channel_id());
                break;
            }
        }
        if let Some(cid) = failed {
            self.channel_close(iface_num, cid);
        }
        Ok(written)
    }

    /// Write outgoing packet for a channel with the given ID - it must be
    /// either in the pairing+credential or encrypted transport (appdata) phase.
    /// Returns `false` if channel is not ready to send a packet.
    pub fn packet_out_channel(
        &mut self,
        iface_num: u8,
        channel_id: u16,
        send_buffer: &[u8],
        packet_buffer: &mut [u8],
    ) -> Result<bool, Error> {
        let (channel, _timing) = self.lookup_channel_mut(iface_num, channel_id)?;
        let res = channel.packet_out(packet_buffer, send_buffer);
        if channel.is_failed() {
            self.channel_close(iface_num, channel_id);
        }
        match res {
            Ok(()) => Ok(true),
            Err(ThpError::NotReady) => Ok(false),
            Err(e) => Err(e.into()),
        }
    }

    /// Decrypt and return a message after `packet_in_channel` returned
    /// `TrezorInResult::MessageReady` or `TrezorInResult::MessageReadyAck`.
    /// Message is considered delivered and sending an ACK to the host is
    /// scheduled.
    pub fn message_out(
        &mut self,
        iface_num: u8,
        channel_id: u16,
        receive_buffer: &mut [u8],
    ) -> Result<(u8, u16, usize), Error> {
        let (channel, _timing) = self.lookup_channel_mut(iface_num, channel_id)?;
        let (sid, message_type, message) = channel.message_out(receive_buffer)?;
        Ok((sid, message_type, message.len()))
    }

    /// Encrypt and start sending application message to the peer. Send buffer
    /// must contain serialized message including the application header
    /// (session id and message type) that is `plaintext_len` long, and there
    /// must be space for at least 16 more bytes in the send buffer.
    pub fn message_in(
        &mut self,
        iface_num: u8,
        channel_id: u16,
        plaintext_len: usize,
        send_buffer: &mut [u8],
    ) -> Result<(), Error> {
        let (channel, timing) = self.lookup_channel_mut(iface_num, channel_id)?;
        channel.message_in(plaintext_len, send_buffer)?;
        timing.update_last_write(Instant::now());
        Ok(())
    }

    /// Resend a message on a channel if it has not been acknowledged by host in
    /// the time limit. Returns false if the maximum retransmission attempts
    /// have been exceeded, true otherwise.
    pub fn message_retransmit(&mut self, iface_num: u8, channel_id: u16) -> Result<bool, Error> {
        let retry = if let Some((ch, _t)) = self.channel_appdata.get_mut(&(iface_num, channel_id)) {
            ch.message_retransmit()?;
            ch.sending_retry()
        } else if let Some((ch, _t)) = self.channel_opening.get_mut(&(iface_num, channel_id)) {
            ch.message_retransmit()?;
            ch.sending_retry()
        } else {
            return Err(CHANNEL_NOT_FOUND);
        };
        match retry {
            None => {
                log::error!(
                    "[{:04x}] Requested to retransmit but not currently sending.",
                    channel_id
                );
                Ok(true)
            }
            Some(r) if r > MAX_RETRANSMISSION_COUNT => {
                log::warn!(
                    "[{:04x}] Closing channel after too many retransmissions.",
                    channel_id
                );
                self.channel_close(iface_num, channel_id);
                Ok(false)
            }
            _ => Ok(true),
        }
    }

    // Returns channel ID of a channel with application message ready to be
    // decrypted. TODO debug only, delete
    pub fn message_out_ready(&self, iface_num: u8) -> Option<u16> {
        self.channel_appdata
            .iter()
            .filter(|&((ifn, _cid), _cht)| *ifn == iface_num)
            .find_map(|((_ifn, cid), (ch, _t))| ch.message_out_ready().then_some(*cid))
    }

    // Returns handshake hash of a channel.
    pub fn handshake_hash(&self, iface_num: u8, channel_id: u16) -> Result<&[u8], Error> {
        let (channel, _timing) = self.lookup_channel(iface_num, channel_id)?;
        Ok(channel.handshake_hash())
    }

    // Returns host's static public key.
    pub fn remote_static_pubkey(&self, iface_num: u8, channel_id: u16) -> Result<&[u8], Error> {
        let (channel, _timing) = self.lookup_channel(iface_num, channel_id)?;
        Ok(channel.remote_static_pubkey())
    }

    // Returns information for a channel:
    // - duration between now and the last time a (non-ACK) packet has been sent
    // - paring state result of handshake (only channels in pairing+credential
    //   phase, channels in encrypted transport return None)
    pub fn channel_info(
        &self,
        iface_num: u8,
        channel_id: u16,
    ) -> Result<(Option<u32>, Option<u8>), Error> {
        let (channel, timing) = self.lookup_channel(iface_num, channel_id)?;
        let pairing_state = match channel.phase() {
            Phase::PairingCredential {
                handshake_pairing_state,
            } => Some(handshake_pairing_state.into()),
            Phase::EncryptedTransport => None,
        };
        let last_write_age_ms = timing
            .last_write_age(Instant::now())
            .map(|duration| duration.to_millis());
        Ok((last_write_age_ms, pairing_state))
    }

    /// Indicate that a pairing+credential phase was successfully finished,
    /// transition channel to encrypted transport (appdata) phase.
    /// The "channel replacement" mechanism happens here - if an open channel
    /// with the same host static public key exists, it is closed and its ID
    /// is returned so that micropython app can migrate the channel's sessions.
    pub fn channel_paired(&mut self, iface_num: u8, channel_id: u16) -> Result<Option<u16>, Error> {
        log::debug!("[{:04x}] Pairing/credential phase complete.", channel_id);
        let (channel, _timing) = self.lookup_channel_mut(iface_num, channel_id)?;
        if channel.is_encrypted_transport() {
            log::error!(
                "[{:04x}] Channel is already in encrypted transport state!",
                channel_id
            );
            return Ok(None);
        }
        // Transition to encrypted transport.
        channel.end_pairing();

        // Replace ENCRYPTED channel with the same host pubkey if there is one.
        let host_key = *channel.remote_static_pubkey();
        let old_channel_id = self
            .channel_appdata
            .iter()
            .find(|&((ifn, cid), (ch, _t))| {
                *ifn == iface_num
                    && *cid != channel_id
                    && ch.is_encrypted_transport()
                    && ch.remote_static_pubkey() == &host_key
            })
            .map(|(_, (ch, _t))| ch.channel_id());
        if let Some(cid) = old_channel_id {
            self.channel_close(iface_num, cid);
        }

        // Delete saved credential as it's no longer needed.
        {
            let mut aux = THP_AUX.try_lock().ok_or(CANNOT_UNLOCK)?;
            aux.delete_credential(iface_num, channel_id);
        }

        Ok(old_channel_id)
    }

    /// Remove a channel and any associated state.
    pub fn channel_close(&mut self, iface_num: u8, channel_id: u16) {
        log::debug!("[{:04x}] Closing channel.", channel_id);
        if let Some((ch, _t)) = self.channel_appdata.remove(&(iface_num, channel_id)) {
            // Pairing/credential channels don't need notification
            // because they don't have sessions.
            if ch.is_encrypted_transport() {
                // Add to channel closed notification queue.
                insert_replace_queue(self.channel_closed.as_mut_view(), (iface_num, channel_id));
            }
        } else {
            self.channel_opening.remove(&(iface_num, channel_id));
        }
        // Delete credential from the credential queue.
        if let Some(mut aux) = THP_AUX.try_lock() {
            aux.delete_credential(iface_num, channel_id);
        }
    }

    /// Close all channels on all interfaces, possibly keeping the one in
    /// `exclude` argument. Channel IDs are not added to `channel_closed`
    /// queue, micropython is responsible for removing sessions of all affected
    /// channels.
    pub fn channel_close_all(&mut self, exclude: Option<u16>) {
        log::warn!("Close all");
        for mux in self.ifaces.values_mut() {
            mux.reset();
        }
        self.channel_appdata
            .retain(|&(_ifn, cid), _ch| Some(cid) == exclude);
        self.channel_opening.clear();
        self.channel_closed.clear();
        if let Some(mut aux) = THP_AUX.try_lock() {
            aux.delete_credential_all();
        }
    }

    /// Get the IDs of channels in encrypted transport phase that have been
    /// closed since this function was last called. Sessions associated with
    /// these channels should be removed.
    pub fn channel_get_closed(&mut self, iface_num: u8) -> Vec<u16, MAX_CHANNELS_APPDATA> {
        let res = Vec::from_iter(
            self.channel_closed
                .iter()
                .filter_map(|(ifn, cid)| (*ifn == iface_num).then_some(*cid)),
        );
        self.channel_closed.retain(|(ifn, _cid)| *ifn != iface_num);
        res
    }

    /// Update the `last_usage` logical timestamp of a channel.
    pub fn channel_update_last_usage(&mut self, channel_id: u16) {
        if let Some(timing) = self
            .channel_appdata
            .iter_mut()
            .filter_map(|((_ifn, cid), (_ch, t))| (*cid == channel_id).then_some(t))
            .chain(
                self.channel_opening
                    .iter_mut()
                    .filter_map(|((_ifn, cid), (_ch, t))| (*cid == channel_id).then_some(t)),
            )
            .next()
        {
            self.last_usage_counter = self.last_usage_counter.wrapping_add(1);
            timing.update_last_usage(self.last_usage_counter);
        }
    }

    /// Returns the ID and relative time in milliseconds of when a channel
    /// should start retransmitting its message. When there are multiple
    /// such channels, the one with the earliest retransmission is returned.
    /// Returns None if no channel is currently transmitting.
    /// The ID can belong to a channel in handshake state, which is not
    /// otherwise exposed to micropython.
    pub fn next_timeout(&self, iface_num: u8) -> Result<Option<(u16, u32)>, Error> {
        let now = Instant::now();
        let mut earliest: Option<(u16, u32)> = None;
        // Get iterator of tuples (channel_id, retry) for channels that are
        // currently sending.
        let sending = self
            .channel_appdata
            .iter()
            .filter_map(|((ifn, _cid), cht)| (*ifn == iface_num).then_some(cht))
            .filter_map(|(ch, t)| ch.sending_retry().map(|retry| (ch.channel_id(), retry, t)))
            .chain(
                self.channel_opening
                    .iter()
                    .filter_map(|((ifn, _cid), cht)| (*ifn == iface_num).then_some(cht))
                    .filter_map(|(ch, t)| {
                        ch.sending_retry().map(|retry| (ch.channel_id(), retry, t))
                    }),
            );
        for (channel_id, retry, timing) in sending {
            let timeout_ms = timing.timeout_from_now(now, retry).to_millis();
            earliest = match (earliest, timeout_ms) {
                // No result yet - update.
                (None, t) => Some((channel_id, t)),
                // Earlier timeout - update.
                (Some((_, t_best)), t_cur) if t_cur < t_best => Some((channel_id, t_cur)),
                // Otherwise keep the current best.
                _ => earliest,
            }
        }
        Ok(earliest)
    }

    /// Ask the host to try again later because the receive buffer is used by
    /// another channel.
    pub fn send_transport_busy(&mut self, iface_num: u8, channel_id: u16) -> Result<(), Error> {
        let (channel, _timing) = self.lookup_channel_mut(iface_num, channel_id)?;
        channel.send_error(TransportError::TransportBusy);
        Ok(())
    }

    /// Abort ongoing handshakes because Trezor's static key is not available.
    pub fn send_device_locked(&mut self, iface_num: u8) -> Result<(), Error> {
        let mut first_err = None;
        for ((ifn, _cid), (ch, _t)) in self.channel_opening.iter_mut() {
            if *ifn != iface_num {
                continue;
            }
            if ch.static_key_required() {
                if let Err(e) = ch.send_device_locked() {
                    // Channel will be closed after the error is sent out.
                    first_err.get_or_insert(e);
                }
            }
        }
        first_err.map_or(Ok(()), |e| Err(e.into()))
    }

    /// Provide Trezor's static key for the ongoing handshake(s). The key is not
    /// copied and the slice can be overwritten after the function returns.
    pub fn handshake_static_key(
        &mut self,
        iface_num: u8,
        local_static_privkey: &[u8],
    ) -> Result<(), Error> {
        let key = local_static_privkey
            .try_into()
            .map_err(|_| Error::ThpError(c"Invalid key length"))?;
        let mut first_err = None;
        for ((ifn, _cid), (ch, t)) in self.channel_opening.iter_mut() {
            if *ifn != iface_num {
                continue;
            }
            if ch.static_key_required() {
                if let Err(e) = ch.set_static_key(key) {
                    first_err.get_or_insert(e);
                }
                // Outgoing message is now ready, update last_write.
                if let Some(0) = ch.sending_retry() {
                    t.update_last_write(Instant::now());
                }
            }
        }
        first_err.map_or(Ok(()), |e| Err(e.into()))
    }

    // Look up channel in pairing/credential/encrypted-transport phase by its id.
    fn lookup_channel_mut(
        &mut self,
        iface_num: u8,
        channel_id: u16,
    ) -> Result<&mut (TrezorChannel, ChannelTiming), Error> {
        self.channel_appdata
            .get_mut(&(iface_num, channel_id))
            .ok_or(CHANNEL_NOT_FOUND)
    }

    // Look up channel in pairing/credential/encrypted-transport phase by its id.
    fn lookup_channel(
        &self,
        iface_num: u8,
        channel_id: u16,
    ) -> Result<&(TrezorChannel, ChannelTiming), Error> {
        self.channel_appdata
            .get(&(iface_num, channel_id))
            .ok_or(CHANNEL_NOT_FOUND)
    }

    // Returns None if `channels` is not full, or ID of its least recently used
    // channel otherwise.
    fn lru_needs_closing<T, const N: usize>(
        channels: &LinearMap<(u8, u16), (T, ChannelTiming), N>,
    ) -> Option<(u8, u16)> {
        if !channels.is_full() {
            return None;
        }
        let ifncid = least_recently_used(
            &mut channels
                .iter()
                .map(|((ifn, cid), (_ch, t))| ((*ifn, *cid), t)),
        );
        assert!(ifncid.is_some());
        ifncid
    }

    // Insert a channel into `LinearMap`. Panic if it is full or the ID is not
    // unique.
    fn insert_channel<T>(
        channels: &mut LinearMapView<(u8, u16), (T, ChannelTiming)>,
        iface_num: u8,
        channel_id: u16,
        channel: T,
        timing: ChannelTiming,
    ) {
        let res = channels.insert((iface_num, channel_id), (channel, timing));
        // should not panic since a slot was freed up before calling this function
        let res = unwrap!(res);
        // should not panic as we don't expect duplicate ids
        assert!(res.is_none());
    }

    // Get unique channel ID for newly allocated channel.
    fn get_channel_id(&self) -> u16 {
        let is_unique = |cid: &u16| {
            self.channel_appdata
                .keys()
                .chain(self.channel_opening.keys())
                .find(|&(_i, c)| c == cid)
                .is_none()
        };
        let mut result = CHANNEL_ID_COUNTER.get();
        while !is_unique(&result) {
            result = CHANNEL_ID_COUNTER.get();
        }
        result
    }
}

// Append element into a queue. Drop first item if full.
fn insert_replace_queue<T>(queue: &mut DequeView<T>, elem: T) {
    if queue.is_full() {
        queue.pop_front();
        log::error!("THP queue full.")
    }
    unwrap!(queue.push_back(elem));
}

/// Context for credential verification callback.
#[derive(Clone)]
pub struct TrezorCredentialVerifier {
    /// Interface ID.
    iface_num: u8,
    /// Channel ID.
    channel_id: u16,
    /// Micropython credential verification function. It is set just before it's
    /// needed to avoid holding long-lived reference to micropython memory
    /// in a global variable.
    verify_fn: Obj,
}

// Required by spin::Mutex to be able to lock verify_fn.
// SAFETY: We are in a single-threaded environment.
unsafe impl Send for TrezorCredentialVerifier {}

impl TrezorCredentialVerifier {
    fn new(iface_num: u8, channel_id: u16) -> Self {
        Self {
            iface_num,
            channel_id,
            verify_fn: Obj::const_none(),
        }
    }
}

impl CredentialVerifier for TrezorCredentialVerifier {
    fn verify(&self, remote_static_pubkey: &[u8], credential: &[u8]) -> PairingState {
        log::debug!("[{:04x}] TrezorCredentialVerifier::verify", self.channel_id);
        let func = || -> Result<PairingState, Error> {
            if self.verify_fn == Obj::const_none()
                || credential.is_empty()
                || remote_static_pubkey.is_empty()
            {
                log::info!("No credential, skipping verification.");
                return Ok(PairingState::Unpaired);
            }
            let res = self
                .verify_fn
                .call_with_n_args(&[remote_static_pubkey.try_into()?, credential.try_into()?])?;
            let ps = PairingState::try_from(u8::try_from(res)?)?;
            // Channel replacement - check if we already trust this key.
            if ps == PairingState::Paired {
                let mut aux = THP_AUX.try_lock().ok_or(CANNOT_UNLOCK)?;
                aux.add_credential(self.iface_num, self.channel_id, credential);
                if aux.host_keys_contain(remote_static_pubkey) {
                    return Ok(PairingState::PairedAutoconnect);
                }
            }
            Ok(ps)
        };
        let res = func();
        match res {
            Ok(ps) => log::debug!("[{:04x}] Result: {}", self.channel_id, ps as u8),
            Err(e) => log::error!(
                "[{:04x}] Credential verification error: {:?}",
                self.channel_id,
                e
            ),
        }
        res.unwrap_or(PairingState::Unpaired)
    }
}

/// Result of `InterfaceContext::packet_in` and
/// `InterfaceContext::packet_in_channel`.
enum TrezorInResult {
    /// Either a valid packet was consumed, or malformed one was ignored. No
    /// further action required.
    None,
    /// Packet should be processed by a channel in pairing+credential or
    /// encrypted transport phase by calling `packet_in_channel`.
    /// If `buffer_size` is `Some` then the receive buffer needs to be at least
    /// as large.
    Route {
        channel_id: u16,
        buffer_size: Option<NonZeroU16>,
    },
    /// Packet caused unrecoverable error and was closed.
    Failed,
    /// Handshake packet requires Trezor's static key. Micropython needs to call
    /// either `InterfaceContext::send_device_locked()` or
    /// `InterfaceContext::static_key()`.
    KeyRequired { try_to_unlock: bool },
    /// Incoming message is ready on a channel, `InterfaceContext::message_out`
    /// should be called. Does not contain ACK bit.
    MessageReady,
    /// Incoming message is ready on a channel, `InterfaceContext::message_out`
    /// should be called. Message contains a valid ACK bit indicating that
    /// outgoing message was received and Trezor can send another one.
    MessageReadyAck,
    /// Valid ACK message was received, indicating that outgoing message was
    /// received and Trezor can send another one.
    Ack,
}

/// Helper data structure, needs to be accessible by credential verification
/// callback when THP_INTERFACES is already locked.
struct Auxiliary {
    /// Host static public keys for open channels in appdata phase. Used for
    /// "channel replacement".
    host_keys: Vec<PubKey, MAX_CHANNELS_APPDATA>,
    /// Credential is copied here during handshake, then picked up by
    /// micropython during pairing+credential phase.
    credentials: Deque<(u8, u16, Vec<u8, MAX_CREDENTIAL_LEN>), MAX_CHANNELS_APPDATA>,
}

impl Auxiliary {
    pub const fn new() -> Self {
        Self {
            host_keys: Vec::new(),
            credentials: Deque::new(),
        }
    }

    pub fn add_credential(&mut self, iface_num: u8, channel_id: u16, credential: &[u8]) {
        let Ok(credential) = Vec::from_slice(credential) else {
            log::error!(
                "[{:04x}] Credential too long: {}",
                channel_id,
                credential.len()
            );
            return;
        };
        insert_replace_queue(
            self.credentials.as_mut_view(),
            (iface_num, channel_id, credential),
        );
    }

    pub fn get_credential(&self, iface_num: u8, channel_id: u16) -> Option<&[u8]> {
        self.credentials
            .iter()
            .find(|&(ifn, cid, _)| ifn == &iface_num && cid == &channel_id)
            .map(|(_, _, cred)| cred.as_slice())
    }

    pub fn delete_credential(&mut self, iface_num: u8, channel_id: u16) {
        self.credentials
            .retain(|(ifn, cid, _)| *ifn != iface_num || *cid != channel_id);
    }

    pub fn delete_credential_all(&mut self) {
        self.credentials.clear();
    }

    pub fn host_keys_copy_from(
        &mut self,
        iface_num: u8,
        channels: &LinearMapView<(u8, u16), (TrezorChannel, ChannelTiming)>,
    ) {
        self.host_keys.clear();
        self.host_keys.extend(
            channels
                .iter()
                .filter(|&((ifn, _cid), (ch, _t))| *ifn == iface_num && ch.is_encrypted_transport())
                .map(|(_, (ch, _t))| *ch.remote_static_pubkey()),
        );
    }

    pub fn host_keys_contain(&self, host_key: &[u8]) -> bool {
        match host_key.try_into() {
            Ok(hk) => self.host_keys.contains(hk),
            _ => false,
        }
    }
}
