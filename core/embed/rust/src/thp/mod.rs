mod crypto;
mod micropython;
mod time;

use crate::{error::Error, micropython::obj::Obj, time::Instant};

use core::num::NonZeroU16;

use heapless::{
    deque::{Deque, DequeView},
    linear_map::{LinearMap, LinearMapView},
    Vec,
};
use spin::{Lazy, Mutex};

use trezor_thp::{
    channel::{
        device::{Channel, ChannelIdAllocator, ChannelOpen, Mux},
        PacketInResult, PairingState, MAX_CREDENTIAL_LEN, PUBKEY_LEN,
    },
    credential::CredentialVerifier,
    error::TransportError,
    ChannelIO, Error as ThpError,
};

use crypto::TrezorCrypto;
use time::ChannelTiming;

// ~ 236B (contains MAX_DEVICE_PROPERTIES_LEN buffer)
type TrezorMux = Mux<TrezorCrypto>;
// ~ 800B
type TrezorChannelOpen = ChannelOpen<TrezorCredentialVerifier, TrezorCrypto>;
// ~ 192B
type TrezorChannel = Channel<TrezorCrypto>;

type PubKey = [u8; PUBKEY_LEN];

// const MAX_DEVICE_PROPERTIES_LEN: usize = 32;
// const MAX_CREDENTIAL_LEN: usize = 96;
// TODO sync with micropython

#[cfg(not(feature = "ble"))]
const MAX_INTERFACES: usize = 1;
#[cfg(feature = "ble")]
const MAX_INTERFACES: usize = 2;

// Per-interface channel limits.
const MAX_CHANNELS_OPENING: usize = 4;
const MAX_CHANNELS_PAIRING: usize = 4;
const MAX_CHANNELS_APPDATA: usize = 8;
const MAX_CHANNELS_ANY: usize = MAX_CHANNELS_OPENING + MAX_CHANNELS_PAIRING + MAX_CHANNELS_APPDATA;

const MAX_RETRANSMISSION_COUNT: u8 = 50;
const CANNOT_UNLOCK: Error = Error::RuntimeError(c"THP state locked");
const CHANNEL_NOT_FOUND: Error = Error::IndexError;

/// Per-interface THP state, in a global variable.
/// Needs to be wrapped in a mutex because even without threads the compiler
/// cannot guarantee that borrowing rules are obeyed.
static THP_INTERFACES: Mutex<LinearMap<u8, InterfaceContext, MAX_INTERFACES>> =
    Mutex::new(LinearMap::new());

/// Auxiliary THP state. Contains data that need to be accessed by
/// TrezorCredentialVerifier::verify while THP_INTERFACES is already locked
/// (host keys, credentials).
static THP_AUX: Mutex<Auxiliary> = Mutex::new(Auxiliary::new());

/// Next channel ID to be allocated. These are unique across interfaces.
static CHANNEL_ID_COUNTER: Lazy<ChannelIdAllocator> =
    Lazy::new(ChannelIdAllocator::new_random::<TrezorCrypto>);

/// State of channels and associated data for single communication interface.
// NOTE: it would be possible for a single struct to hold the state for all
// interfaces and save a bit of flash spce - there would only have to be
// per-interface mux and the LinearMap keys would then be (u8, u16).
// Currently around 6KiB with 4/4/8 opening/pairing/appdata.
struct InterfaceContext {
    /// Interface identifier.
    iface_num: u8,
    /// Handles broadcast messages, channel allocation, CodecV1 responses.
    mux: TrezorMux,
    /// Channels in the opening phase. One element is larger than other channels
    /// due to the Noise handshake state and an internal buffer that needs
    /// to fit MAX_CREDENTIAL_LEN + 48 bytes.
    /// These channels are not exposed to python except for retransmission
    /// handling.
    channel_opening: LinearMap<u16, TrezorChannelOpen, MAX_CHANNELS_OPENING>,
    /// Channels in the pairing+credential phase.
    channel_pairing: LinearMap<u16, TrezorChannel, MAX_CHANNELS_PAIRING>,
    /// Channels in the encrypted transport phase.
    channel_appdata: LinearMap<u16, TrezorChannel, MAX_CHANNELS_APPDATA>,
    /// Whenever a channel is closed during send/receive error, python needs to
    /// be notified in order to delete the associated sessions. This queue holds
    /// the IDs of such channels. Only channels in `channel_appdata` are
    /// affected because other channels don't have sessions.
    channel_closed: Deque<u16, MAX_CHANNELS_APPDATA>,
    /// Timing data associated with channels on this interface. Used to compute
    /// retransmission timeouts, channel preemption, and which channel to
    /// replace when at full capacity.
    timing: LinearMap<u16, ChannelTiming, MAX_CHANNELS_ANY>,
    /// Sort of logical clock that is increased every time
    /// [`ChannelTiming::last_usage`] is increased.
    last_usage_counter: u32,
}

impl InterfaceContext {
    /// Create new initial interface context. Returns error when
    /// `device_properties` is longer than `MAX_DEVICE_PROPERTIES_LEN`.
    pub fn new(iface_num: u8, device_properties: &[u8]) -> Result<Self, Error> {
        Ok(Self {
            iface_num,
            mux: TrezorMux::new(device_properties)?,
            channel_opening: LinearMap::new(),
            channel_pairing: LinearMap::new(),
            channel_appdata: LinearMap::new(),
            channel_closed: Deque::new(),
            timing: LinearMap::new(),
            last_usage_counter: 0,
        })
    }

    /// Process a packet received by the interface. Returns [`TrezorInResult`]
    /// which indicates if anything else needs to be done with the packet.
    pub fn packet_in(
        &mut self,
        packet_buffer: &[u8],
        credential_fn: Obj,
    ) -> Result<TrezorInResult, Error> {
        let pir = self.mux.packet_in(packet_buffer, &mut []);
        let res = match pir {
            PacketInResult::Accepted { .. } => TrezorInResult::None,
            PacketInResult::Ignored { .. } => TrezorInResult::None,
            PacketInResult::Route {
                channel_id,
                buffer_size,
            } => {
                if self.channel_opening.contains_key(&channel_id) {
                    return self.packet_in_handshake(channel_id, packet_buffer, credential_fn);
                }
                if !self.channel_appdata.contains_key(&channel_id)
                    && !self.channel_pairing.contains_key(&channel_id)
                {
                    self.mux.send_unallocated_channel(channel_id)?;
                    log::debug!(
                        "[{:04x}] Received packet for unallocated channel.",
                        channel_id
                    );
                    return Ok(TrezorInResult::None);
                }
                TrezorInResult::Route {
                    channel_id,
                    buffer_size,
                }
            }
            PacketInResult::ChannelAllocation => {
                // Return from function and call Self::channel_alloc - we need to
                // borrow all interfaces to check for id uniqueness.
                TrezorInResult::ChannelAllocation
            }
            _ => {
                return Err(Error::RuntimeError(c"Unexpected PacketInResult"));
            }
        };
        Ok(res)
    }

    /// Needs to be called when `packet_in` returns
    /// `TrezorInResult::ChannelAllocation`. Allocates a channel and starts the
    /// handshake process. Closes the oldest channel in handshake phase if
    /// needed.
    pub fn packet_in_alloc(
        interfaces: &mut LinearMap<u8, InterfaceContext, MAX_INTERFACES>,
        iface_num: u8,
    ) -> Result<(), Error> {
        let channel_id = Self::get_channel_id(interfaces);
        let ifctx = unwrap!(interfaces.get_mut(&iface_num));
        let channel = ifctx.mux.channel_alloc(
            channel_id,
            TrezorCredentialVerifier::new(iface_num, channel_id),
        )?;

        if let Some(cid) = Self::lru_needs_closing(&ifctx.channel_opening, &ifctx.timing) {
            ifctx.channel_close(cid);
        }
        Self::insert_channel(ifctx.channel_opening.as_mut_view(), channel_id, channel);

        let res = ifctx
            .timing
            .insert(channel_id, ChannelTiming::new(Instant::now()));
        if res.is_err() {
            // This should never happen because the number of elements in `timing` is equal
            // to `channel_opening`+`channel_pairing`+`channel_appdata` and if it was full
            // we just freed up one slot. If it happens anyway, continue in degraded mode
            // instead of panicking - retransmission won't work & `lru_needs_closing` will
            // return it first.
            log::error!(
                "[{:04x}] Cannot create timing information, retransmissions disabled.",
                channel_id
            );
        }
        ifctx.channel_update_last_usage(channel_id);
        Ok(())
    }

    // Called by `packet_in` to process a packet for channel in the handshake phase.
    // Might invoke the python credential verification callback.
    fn packet_in_handshake(
        &mut self,
        channel_id: u16,
        packet_buffer: &[u8],
        credential_fn: Obj,
    ) -> Result<TrezorInResult, Error> {
        let channel = self
            .channel_opening
            .get_mut(&channel_id)
            .ok_or(CHANNEL_NOT_FOUND)?;
        // Set all host keys aside so that TrezorCredentialVerifier can look up
        // peer key for channel replacement purposes. Does not work across interfaces.
        // As a possible optimization we can check packet's control byte and only do it
        // if it's HandshakeCompletionRequest.
        // Alternatively we can copy these to micropython before credential_fn is
        // called.
        {
            let mut aux = THP_AUX.try_lock().ok_or(CANNOT_UNLOCK)?;
            aux.host_keys_copy_from(self.channel_appdata.as_view());
        };
        // Set credential verification callback here - we don't want to keep a
        // longer-lived reference as it could either keep the function alive
        // across session restart (if GC is aware of it), or we could end up
        // holding a reference to non-existent object (if GC is not aware of it).
        channel.credential_verifier().verify_fn = credential_fn;
        let pir = channel.packet_in(packet_buffer, &mut []);
        channel.credential_verifier().verify_fn = Obj::const_none();
        if pir.got_ack() {
            if let Some(t) = self.timing.get_mut(&channel_id) {
                t.read_ack(Instant::now());
            }
        }
        let res = match pir {
            PacketInResult::Accepted { .. } => TrezorInResult::None,
            PacketInResult::Ignored { .. } => TrezorInResult::None,
            PacketInResult::Failed { .. } => {
                log::error!("[{:04x}] Handshake failed.", channel_id);
                self.channel_close(channel_id);
                // micropython doesn't know about the channel, no point returning Failure
                return Ok(TrezorInResult::None);
            }
            PacketInResult::HandshakeKeyRequired { try_to_unlock } => {
                TrezorInResult::KeyRequired { try_to_unlock }
            }
            _ => {
                return Err(Error::RuntimeError(c"Unexpected PacketInResult"));
            }
        };
        if channel.handshake_done() {
            let channel = unwrap!(self.channel_opening.remove(&channel_id));
            let channel = channel.complete()?;

            if let Some(cid) = Self::lru_needs_closing(&self.channel_pairing, &self.timing) {
                self.channel_close(cid);
            }
            Self::insert_channel(self.channel_pairing.as_mut_view(), channel_id, channel);

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
        channel_id: u16,
        packet_buffer: &[u8],
        receive_buffer: &mut [u8],
    ) -> Result<TrezorInResult, Error> {
        let channel = self.lookup_channel_mut(channel_id)?;
        let pir = channel.packet_in(packet_buffer, receive_buffer);
        // log::debug!("[{:04x}] PacketInResult: {:?}", channel_id, pir);
        let res = match pir {
            PacketInResult::Accepted {
                ack_received,
                message_ready,
                ..
            } => match (message_ready, ack_received) {
                (true, true) => TrezorInResult::MessageReadyAck,
                (true, false) => TrezorInResult::MessageReady,
                (false, true) => TrezorInResult::Ack,
                _ => TrezorInResult::None,
            },
            PacketInResult::Ignored { .. } => TrezorInResult::None,
            PacketInResult::Failed { .. } | PacketInResult::TransportError { .. } => {
                self.channel_close(channel_id);
                TrezorInResult::Failed
            }
            _ => {
                return Err(Error::RuntimeError(c"Unexpected PacketInResult"));
            }
        };
        if pir.got_ack() {
            if let Some(t) = self.timing.get_mut(&channel_id) {
                t.read_ack(Instant::now());
            }
        }
        Ok(res)
    }

    /// Write outgoing packet for the broadcast channel or any channel in the
    /// handshake phase. Returns false if no such packet is ready to be
    /// sent.
    pub fn packet_out(&mut self, packet_buffer: &mut [u8]) -> Result<bool, Error> {
        if self.mux.packet_out_ready() {
            self.mux.packet_out(packet_buffer, &[])?;
            return Ok(true);
        }
        let mut written = false;
        let mut failed = None;
        for channel in self.channel_opening.values_mut() {
            if channel.packet_out_ready() {
                channel.packet_out(packet_buffer, &[])?;
                if let Some(t) = self.timing.get_mut(&channel.channel_id()) {
                    t.update_last_write(Instant::now(), Some(packet_buffer));
                }
                written = true;
                failed = channel.handshake_failed().then_some(channel.channel_id());
                break;
            }
        }
        if let Some(cid) = failed {
            self.channel_close(cid);
        }
        Ok(written)
    }

    /// Write outgoing packet for a channel with the given ID - it must be
    /// either in the pairing+credential or encrypted transport (appdata) phase.
    /// Returns `false` if channel is not ready to send a packet.
    pub fn packet_out_channel(
        &mut self,
        channel_id: u16,
        send_buffer: &[u8],
        packet_buffer: &mut [u8],
    ) -> Result<bool, Error> {
        let channel = self.lookup_channel_mut(channel_id)?;
        let res = channel.packet_out(packet_buffer, send_buffer);
        if channel.is_failed() {
            self.channel_close(channel_id);
        }
        match res {
            Err(ThpError::NotReady) => Ok(false),
            Ok(()) => {
                if let Some(t) = self.timing.get_mut(&channel_id) {
                    t.update_last_write(Instant::now(), Some(packet_buffer));
                }
                Ok(true)
            }
            Err(e) => Err(e.into()),
        }
    }

    /// Decrypt and return a message after `packet_in_channel` returned
    /// `TrezorInResult::MessageReady` or `TrezorInResult::MessageReadyAck`.
    /// Message is considered delivered and sending an ACK to the host is
    /// scheduled.
    pub fn message_out<'a>(
        &'a mut self,
        channel_id: u16,
        receive_buffer: &'a mut [u8],
    ) -> Result<(u8, u16, &'a [u8]), Error> {
        let channel = self.lookup_channel_mut(channel_id)?;
        Ok(channel.message_out(receive_buffer)?)
    }

    /// Encrypt and start sending application message to the peer. Send buffer
    /// must contain serialized message including the application header
    /// (session id and message type) that is `plaintext_len` long, and there
    /// must be space for at least 16 more bytes in the send buffer.
    pub fn message_in(
        &mut self,
        channel_id: u16,
        plaintext_len: usize,
        send_buffer: &mut [u8],
    ) -> Result<(), Error> {
        let channel = self.lookup_channel_mut(channel_id)?;
        Ok(channel.message_in(plaintext_len, send_buffer)?)
    }

    /// Resend a message on a channel if it has not been acknowledged by host in
    /// the time limit. Returns false if the maximum retransmission attempts
    /// have been exceeded, true otherwise.
    pub fn message_retransmit(&mut self, channel_id: u16) -> Result<bool, Error> {
        let retry = if let Some(ch) = self.channel_appdata.get_mut(&channel_id) {
            ch.message_retransmit()?;
            ch.sending_retry()
        } else if let Some(ch) = self.channel_pairing.get_mut(&channel_id) {
            ch.message_retransmit()?;
            ch.sending_retry()
        } else if let Some(ch) = self.channel_opening.get_mut(&channel_id) {
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
                self.channel_close(channel_id);
                Ok(false)
            }
            Some(_) => {
                // Update last write so that we don't end up retransmitting too quickly if
                // writes are blocked for some reason.
                if let Some(t) = self.timing.get_mut(&channel_id) {
                    t.update_last_write(Instant::now(), None);
                }
                Ok(true)
            }
        }
    }

    // Returns channel ID of a channel with application message ready to be
    // decrypted. TODO debug only, delete
    pub fn message_out_ready(&self) -> Option<u16> {
        self.channel_appdata
            .iter()
            .chain(self.channel_pairing.iter())
            .find_map(|(cid, ch)| ch.message_out_ready().then_some(*cid))
    }

    // Returns handshake hash of a channel.
    pub fn handshake_hash(&self, channel_id: u16) -> Result<&[u8], Error> {
        let ch = self.lookup_channel(channel_id)?;
        Ok(ch.handshake_hash())
    }

    // Returns host's static public key.
    pub fn remote_static_pubkey(&self, channel_id: u16) -> Result<&[u8], Error> {
        let ch = self.lookup_channel(channel_id)?;
        Ok(ch.remote_static_pubkey())
    }

    // Returns information for a channel:
    // - duration between now and the last time a (non-ACK) packet has been sent
    // - paring state result of handshake (only channels in pairing+credential
    //   phase, channels in appdata return None)
    pub fn channel_info(&self, channel_id: u16) -> Result<(Option<u32>, Option<u8>), Error> {
        let pairing_state = if self.channel_appdata.contains_key(&channel_id) {
            None
        } else if let Some(ch) = self.channel_pairing.get(&channel_id) {
            Some(ch.handshake_pairing_state().into())
        } else {
            return Err(CHANNEL_NOT_FOUND);
        };
        let last_write_age_ms = self
            .timing
            .get(&channel_id)
            .and_then(|t| t.last_write_age(Instant::now()))
            .map(|t| t.to_millis());
        Ok((last_write_age_ms, pairing_state))
    }

    /// Indicate that a pairing+credential phase was successfully finished,
    /// transition channel to encrypted transport (appdata) phase.
    /// The "channel replacement" mechanism happens here - if an open channel
    /// with the same host static public key exists, it is closed and its ID
    /// is returned so that micropython app can migrate the channel's sessions.
    pub fn channel_paired(&mut self, channel_id: u16) -> Result<Option<u16>, Error> {
        log::debug!("[{:04x}] Pairing/credential phase complete.", channel_id);
        let channel = self
            .channel_pairing
            .remove(&channel_id)
            .ok_or(CHANNEL_NOT_FOUND)?;
        let host_key = *channel.remote_static_pubkey();

        // Replace ENCRYPTED channel with the same host pubkey if there is one.
        let old_channel_id = self
            .channel_appdata
            .values()
            .find(|ch| ch.remote_static_pubkey() == &host_key)
            .map(|ch| ch.channel_id());
        if let Some(cid) = old_channel_id {
            self.channel_close(cid);
        }

        if let Some(cid) = Self::lru_needs_closing(&self.channel_appdata, &self.timing) {
            self.channel_close(cid);
        }
        Self::insert_channel(self.channel_appdata.as_mut_view(), channel_id, channel);

        // Delete saved credential as it's no longer needed.
        {
            let mut aux = THP_AUX.try_lock().ok_or(CANNOT_UNLOCK)?;
            aux.delete_credential(channel_id);
        }

        Ok(old_channel_id)
    }

    /// Remove a channel and any associated state.
    pub fn channel_close(&mut self, channel_id: u16) {
        log::debug!("[{:04x}] Closing channel.", channel_id);
        if self.channel_appdata.remove(&channel_id).is_some() {
            // Add to channel closed notification queue.
            insert_replace_queue(self.channel_closed.as_mut_view(), channel_id);
        } else if self.channel_pairing.remove(&channel_id).is_some() {
            // Pairing/credential channels don't need notification
            // because they don't have sessions.
        } else {
            self.channel_opening.remove(&channel_id);
        }
        self.timing.remove(&channel_id);
        // Delete credential from the credential queue.
        if let Some(mut aux) = THP_AUX.try_lock() {
            aux.delete_credential(channel_id);
        }
    }

    /// Close all channels on this interface, possibly keeping the one in
    /// `exclude` argument. Channel IDs are not added to `channel_closed`
    /// queue, micropython is responsible for removing sessions of all affected
    /// channels.
    pub fn channel_close_all(&mut self, exclude: Option<u16>) {
        log::warn!("Close all");
        self.mux.reset();
        self.channel_appdata
            .retain(|&cid, _ch| Some(cid) == exclude);
        self.channel_pairing.clear();
        self.channel_opening.clear();
        self.channel_closed.clear();
        self.timing.retain(|&cid, _ch| Some(cid) == exclude);
        if let Some(mut aux) = THP_AUX.try_lock() {
            aux.delete_credential_all();
        }
    }

    /// Get the IDs of channels in encrypted transport phase that have been
    /// closed since this function was last called. Sessions associated with
    /// these channels should be removed.
    pub fn channel_get_closed(&mut self) -> Vec<u16, MAX_CHANNELS_APPDATA> {
        let res = unwrap!(Vec::from_slice(self.channel_closed.make_contiguous()));
        self.channel_closed.clear();
        res
    }

    /// Update the `last_usage` logical timestamp of a channel.
    pub fn channel_update_last_usage(&mut self, channel_id: u16) {
        if let Some(t) = self.timing.get_mut(&channel_id) {
            self.last_usage_counter = self.last_usage_counter.wrapping_add(1);
            t.update_last_usage(self.last_usage_counter);
        }
    }

    /// Returns the ID and relative time in milliseconds of when a channel
    /// should start retransmitting its message. When there are multiple
    /// such channels, the one with the earliest retransmission is returned.
    /// Returns None if no channel is currently transmitting.
    /// The ID can belong to a channel in handshake state, which is not
    /// otherwise exposed to micropython.
    pub fn next_timeout(&self) -> Result<Option<(u16, u32)>, Error> {
        let now = Instant::now();
        let mut earliest: Option<(u16, u32)> = None;
        // Get iterator of tuples (channel_id, retry) for channels that are
        // currently sending.
        let sending = self
            .channel_appdata
            .values()
            .filter_map(|ch| ch.sending_retry().map(|retry| (ch.channel_id(), retry)))
            .chain(
                self.channel_pairing
                    .values()
                    .filter_map(|ch| ch.sending_retry().map(|retry| (ch.channel_id(), retry))),
            )
            .chain(
                self.channel_opening
                    .values()
                    .filter_map(|ch| ch.sending_retry().map(|retry| (ch.channel_id(), retry))),
            );
        for (channel_id, retry) in sending {
            let timeout_ms = self
                .timing
                .get(&channel_id)
                .map(|t| t.timeout_from_now(now, retry).to_millis());
            /*
            log::debug!(
                "cid:{:04x} retry:{} ms:{}",
                channel_id,
                retry,
                timeout_ms.unwrap_or(9999)
            );
            */
            let Some(timeout_ms) = timeout_ms else {
                continue;
            };
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

    /// Abort ongoing handshakes because Trezor's static key is not available.
    pub fn send_device_locked(&mut self) -> Result<(), Error> {
        for ch in self.channel_opening.values_mut() {
            if ch.static_key_required() {
                ch.send_device_locked()?;
                // Channel will be closed after the error is sent out.
            }
        }
        Ok(())
    }

    /// Ask the host to try again later because the receive buffer is used by
    /// another channel.
    pub fn send_transport_busy(&mut self, channel_id: u16) -> Result<(), Error> {
        let channel = self.lookup_channel_mut(channel_id)?;
        channel.send_error(TransportError::TransportBusy);
        Ok(())
    }

    /// Provide Trezor's static key for the ongoing handshake. The key is not
    /// copied and the slice can be overwritten after the function returns.
    pub fn handshake_static_key(&mut self, local_static_privkey: &[u8]) -> Result<(), Error> {
        for ch in self.channel_opening.values_mut() {
            if ch.static_key_required() {
                ch.set_static_key(
                    local_static_privkey
                        .try_into()
                        .map_err(|_| Error::ValueError(c"Invalid key length"))?,
                )?;
            }
        }
        Ok(())
    }

    // Look up channel in `channel_appdata` and `channel_pairing` by its id.
    fn lookup_channel_mut(&mut self, channel_id: u16) -> Result<&mut TrezorChannel, Error> {
        self.channel_appdata
            .iter_mut()
            .chain(self.channel_pairing.iter_mut())
            .find(|&(cid, _)| cid == &channel_id)
            .map(|(_, ch)| ch)
            .ok_or(CHANNEL_NOT_FOUND)
    }

    // Look up channel in `channel_appdata` and `channel_pairing` by its id.
    fn lookup_channel(&self, channel_id: u16) -> Result<&TrezorChannel, Error> {
        self.channel_appdata
            .iter()
            .chain(self.channel_pairing.iter())
            .find(|&(cid, _)| cid == &channel_id)
            .map(|(_, ch)| ch)
            .ok_or(CHANNEL_NOT_FOUND)
    }

    // Returns ID of the least recently used channel in a given `LinearMap`.
    fn least_recently_used<T>(
        channels: &LinearMapView<u16, T>,
        timing: &LinearMapView<u16, ChannelTiming>,
    ) -> Option<u16> {
        let mut oldest = None;
        for channel_id in channels.keys() {
            // If a channel is missing from timing for some reason (it shouldn't),
            // remove it first.
            let last_used = timing.get(channel_id).map(|t| t.last_usage()).unwrap_or(0);
            match oldest {
                None => {
                    oldest = Some((*channel_id, last_used));
                }
                Some((_oldest_cid, oldest_val)) if last_used < oldest_val => {
                    oldest = Some((*channel_id, last_used));
                }
                _ => {}
            }
        }
        oldest.map(|(cid, _)| cid)
    }

    // Returns None if `channels` is not full, or ID of its least recently used
    // channel otherwise.
    fn lru_needs_closing<T, const N: usize>(
        channels: &LinearMap<u16, T, N>,
        timing: &LinearMap<u16, ChannelTiming, MAX_CHANNELS_ANY>,
    ) -> Option<u16> {
        if !channels.is_full() {
            return None;
        }
        let cid = Self::least_recently_used(channels.as_view(), timing.as_view());
        assert!(cid.is_some());
        cid
    }

    // Insert a channel into `LinearMap`. Panic if it is full or the ID is not
    // unique.
    fn insert_channel<T>(channels: &mut LinearMapView<u16, T>, channel_id: u16, channel: T) {
        let res = channels.insert(channel_id, channel);
        // should not panic since a slot was freed up before calling this function
        let res = unwrap!(res);
        // should not panic as we don't expect duplicate ids
        assert!(res.is_none());
    }

    // Get unique channel ID for newly allocated channel.
    fn get_channel_id(interfaces: &LinearMap<u8, InterfaceContext, MAX_INTERFACES>) -> u16 {
        let is_unique = |cid: &u16| {
            for ifctx in interfaces.values() {
                if ifctx.channel_appdata.contains_key(cid)
                    || ifctx.channel_pairing.contains_key(cid)
                    || ifctx.channel_opening.contains_key(cid)
                {
                    return false;
                }
            }
            true
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
            let mut aux = unwrap!(THP_AUX.try_lock());
            let res = self.verify_fn.call_with_n_args(&[
                self.channel_id.into(),
                remote_static_pubkey.try_into()?,
                credential.try_into()?,
            ])?;
            let ps = PairingState::try_from(u8::try_from(res)?)?;
            // Channel replacement - check if we already trust this key.
            if ps == PairingState::Paired {
                aux.add_credential(self.channel_id, credential);
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
    /// Channel was allocated and requires ID assignment. This result is not
    /// propagated to micropython.
    ChannelAllocation,
}

/// Helper data structure, needs to be accessible by credential verification
/// callback when THP_INTERFACES is already locked.
struct Auxiliary {
    /// Host static public keys for open channels in appdata phase. Used for
    /// "channel replacement".
    host_keys: Vec<PubKey, MAX_CHANNELS_APPDATA>,
    /// Credential is copied here during handshake, then picked up by
    /// micropython during pairing+credential phase.
    credentials: Deque<(u16, Vec<u8, MAX_CREDENTIAL_LEN>), MAX_CHANNELS_PAIRING>,
}

impl Auxiliary {
    pub const fn new() -> Self {
        Self {
            host_keys: Vec::new(),
            credentials: Deque::new(),
        }
    }

    pub fn add_credential(&mut self, channel_id: u16, credential: &[u8]) {
        let Ok(credential) = Vec::from_slice(credential) else {
            log::error!(
                "[{:04x}] Credential too long: {}",
                channel_id,
                credential.len()
            );
            return;
        };
        insert_replace_queue(self.credentials.as_mut_view(), (channel_id, credential));
    }

    pub fn get_credential(&self, channel_id: u16) -> Option<&[u8]> {
        self.credentials
            .iter()
            .find(|&(cid, _)| cid == &channel_id)
            .map(|(_, cred)| cred.as_slice())
    }

    pub fn delete_credential(&mut self, channel_id: u16) {
        self.credentials.retain(|(cid, _)| *cid != channel_id);
    }

    pub fn delete_credential_all(&mut self) {
        self.credentials.clear();
    }

    pub fn host_keys_copy_from(&mut self, channels: &LinearMapView<u16, TrezorChannel>) {
        self.host_keys.clear();
        self.host_keys
            .extend(channels.values().map(|ch| *ch.remote_static_pubkey()));
    }

    pub fn host_keys_contain(&self, host_key: &[u8]) -> bool {
        match host_key.try_into() {
            Ok(hk) => self.host_keys.contains(hk),
            _ => false,
        }
    }
}
