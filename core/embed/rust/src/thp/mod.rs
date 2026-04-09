mod crypto;
mod micropython;
mod time;

use crate::{error::Error, micropython::obj::Obj, time::Instant};

use heapless::{
    linear_map::{LinearMap, LinearMapView},
    Deque, Vec,
};
use spin::{Lazy, Mutex};

use trezor_thp::{
    channel::{
        device::{Channel, ChannelIdAllocator, ChannelOpen, Mux},
        PacketInResult, PairingState, PUBKEY_LEN,
    },
    credential::CredentialVerifier,
    error::TransportError,
    ChannelIO, Error as ThpError,
};

use crypto::TrezorCrypto;
use time::ChannelTiming;

type TrezorMux = Mux<TrezorCrypto>;
type TrezorChannelOpen = ChannelOpen<TrezorCredentialVerifier, TrezorCrypto>;
type TrezorChannel = Channel<TrezorCrypto>;

type PubKey = [u8; PUBKEY_LEN];

const MAX_DEVICE_PROPERTIES_LEN: usize = 32;
const MAX_CREDENTIAL_LEN: usize = 96; // TODO sync with trezor-thp & micropython

#[cfg(not(feature = "ble"))]
const MAX_INTERFACES: usize = 1;
#[cfg(feature = "ble")]
const MAX_INTERFACES: usize = 2;

// Per-interface channel limits.
// TODO probably too generous - 2/2/10?
const MAX_CHANNELS_OPENING: usize = 4;
const MAX_CHANNELS_PAIRING: usize = 4;
const MAX_CHANNELS_APPDATA: usize = 8;
const MAX_CHANNELS_ANY: usize = MAX_CHANNELS_OPENING + MAX_CHANNELS_PAIRING + MAX_CHANNELS_APPDATA;

const MAX_RETRANSMISSION_COUNT: u8 = 50;
const CANNOT_UNLOCK: Error = Error::RuntimeError(c"THP state locked");
const CHANNEL_NOT_FOUND: Error = Error::IndexError;

// Per-interface THP state, in a global variable.
// TODO explain locking
static THP_INTERFACES: Mutex<LinearMap<u8, InterfaceContext, MAX_INTERFACES>> =
    Mutex::new(LinearMap::new());

// Auxiliary THP state. Depending on the struct member, it is here and not in
// THP_INTERFACES for one of two reasons:
// - it is not scoped to an interface (channel id counter)
// - it needs to be accessed by TrezorCredentialVerifier::verify while
//   THP_INTERFACES is already locked (host keys, credentials)
static THP_AUX: Mutex<Auxiliary> = Mutex::new(Auxiliary::new());

static CHANNEL_ID_COUNTER: Lazy<ChannelIdAllocator> =
    Lazy::new(|| ChannelIdAllocator::new_random::<TrezorCrypto>());

struct InterfaceContext {
    iface_num: u8,
    mux: TrezorMux,
    channel_opening: LinearMap<u16, TrezorChannelOpen, MAX_CHANNELS_OPENING>,
    channel_pairing: LinearMap<u16, TrezorChannel, MAX_CHANNELS_PAIRING>,
    channel_appdata: LinearMap<u16, TrezorChannel, MAX_CHANNELS_APPDATA>,
    timing: LinearMap<u16, ChannelTiming, MAX_CHANNELS_ANY>,
    device_properties: Vec<u8, MAX_DEVICE_PROPERTIES_LEN>,
    last_usage_counter: u32,
}

impl InterfaceContext {
    pub fn new(iface_num: u8, device_properties: &[u8]) -> Self {
        let device_properties = unwrap!(Vec::from_slice(device_properties));
        Self {
            iface_num,
            mux: TrezorMux::new(),
            channel_opening: LinearMap::new(),
            channel_pairing: LinearMap::new(),
            channel_appdata: LinearMap::new(),
            timing: LinearMap::new(),
            device_properties,
            last_usage_counter: 0,
        }
    }

    pub fn packet_in(
        &mut self,
        packet_buffer: &[u8],
        credential_fn: Obj,
    ) -> Result<TrezorInResult, Error> {
        let pir = self.mux.packet_in(packet_buffer, &mut []);
        let res = match pir {
            PacketInResult::Accepted { .. } => TrezorInResult::None,
            PacketInResult::Ignored { .. } => TrezorInResult::None,
            PacketInResult::Route { channel_id } => {
                if self.channel_opening.contains_key(&channel_id) {
                    return self.packet_in_handshake(channel_id, packet_buffer, credential_fn);
                }
                if !self.channel_appdata.contains_key(&channel_id)
                    && !self.channel_pairing.contains_key(&channel_id)
                {
                    self.mux.send_unallocated_channel(channel_id)?;
                    // log::debug!("Received packet for unallocated channel.");
                    return Ok(TrezorInResult::None);
                }
                TrezorInResult::Route(channel_id)
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

    pub fn packet_in_alloc(
        interfaces: &mut LinearMap<u8, InterfaceContext, MAX_INTERFACES>,
        iface_num: u8,
    ) -> Result<(), Error> {
        let channel_id = Self::get_channel_id(interfaces);
        let ifctx = unwrap!(interfaces.get_mut(&iface_num));
        let channel = ifctx.mux.channel_alloc(
            channel_id,
            TrezorCredentialVerifier::new(iface_num, channel_id, ifctx.device_properties.clone()),
        )?;
        Self::insert_replace_lru(
            ifctx.channel_opening.as_mut_view(),
            ifctx.timing.as_mut_view(),
            channel_id,
            channel,
        );

        let res = ifctx
            .timing
            .insert(channel_id, ChannelTiming::new(Instant::now()));
        let res = unwrap!(res); // should not happen TODO why
        assert!(res.is_none()); // id collisions not expected

        ifctx.channel_update_last_usage(channel_id);
        Ok(())
    }

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
                // log::error!("[{}] Handshake failed.", channel_id);
                self.channel_close(channel_id);
                // micropython doesn't know about the channel, no point returning Failure
                return Ok(TrezorInResult::None);
            }
            PacketInResult::HandshakeKeyRequired { try_to_unlock } => {
                TrezorInResult::KeyRequired(try_to_unlock)
            }
            _ => {
                return Err(Error::RuntimeError(c"Unexpected PacketInResult"));
            }
        };
        if channel.handshake_done() {
            let channel = unwrap!(self.channel_opening.remove(&channel_id));
            let channel = channel.complete()?;
            Self::insert_replace_lru(
                &mut self.channel_pairing,
                &mut self.timing,
                channel_id,
                channel,
            );
            self.channel_update_last_usage(channel_id);
        }
        Ok(res)
    }

    pub fn packet_in_channel(
        &mut self,
        channel_id: u16,
        packet_buffer: &[u8],
        receive_buffer: &mut [u8],
    ) -> Result<TrezorInResult, Error> {
        let channel = self.lookup_channel_mut(channel_id)?;
        let pir = channel.packet_in(packet_buffer, receive_buffer);
        // log::debug!("pir: {:?}", pir);
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
                    t.write_packet(Instant::now(), packet_buffer);
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
                    t.write_packet(Instant::now(), packet_buffer);
                }
                Ok(true)
            }
            Err(e) => Err(e.into()),
        }
    }

    pub fn message_out<'a>(
        &'a mut self,
        channel_id: u16,
        receive_buffer: &'a mut [u8],
    ) -> Result<(u8, u16, &'a [u8]), Error> {
        let channel = self.lookup_channel_mut(channel_id)?;
        Ok(channel.message_out(receive_buffer)?)
    }

    pub fn message_in(
        &mut self,
        channel_id: u16,
        plaintext_len: usize,
        send_buffer: &mut [u8],
    ) -> Result<(), Error> {
        let channel = self.lookup_channel_mut(channel_id)?;
        Ok(channel.message_in(plaintext_len, send_buffer)?)
    }

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
            Some(r) if r > MAX_RETRANSMISSION_COUNT => {
                // log::warn!("[{}] Closing channel after too many retransmissions.",
                // channel_id);
                self.channel_close(channel_id);
                Ok(false)
            }
            None => {
                // log::error!("[{}] Requested to retransmit but not currently sending.",
                // channel_id);
                Ok(true)
            }
            _ => Ok(true),
        }
    }

    // TODO delete
    pub fn message_out_ready(&self) -> Option<u16> {
        for channel in self.channel_appdata.values() {
            if channel.message_out_ready() {
                return Some(channel.channel_id());
            }
        }
        for channel in self.channel_pairing.values() {
            if channel.message_out_ready() {
                return Some(channel.channel_id());
            }
        }
        None
    }

    pub fn handshake_hash(&self, channel_id: u16) -> Result<&[u8], Error> {
        let ch = self.lookup_channel(channel_id)?;
        Ok(ch.handshake_hash())
    }

    pub fn remote_static_pubkey(&self, channel_id: u16) -> Result<&[u8], Error> {
        let ch = self.lookup_channel(channel_id)?;
        Ok(ch.remote_static_key())
    }

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
            .and_then(|t| t.last_write_age(Instant::now()));
        Ok((last_write_age_ms, pairing_state))
    }

    pub fn channel_paired(&mut self, channel_id: u16) -> Result<Option<u16>, Error> {
        // log::debug!("[{}] Pairing/credential phase complete.", channel_id);
        let channel = self
            .channel_pairing
            .remove(&channel_id)
            .ok_or(CHANNEL_NOT_FOUND)?;
        let host_key = *channel.remote_static_key();

        // Replace ENCRYPTED channel with the same host pubkey if there is one.
        let old_channel_id = self
            .channel_appdata
            .values()
            .find(|ch| ch.remote_static_key() == &host_key)
            .map(|ch| ch.channel_id());
        if let Some(cid) = old_channel_id {
            self.channel_close(cid);
        }

        Self::insert_replace_lru(
            &mut self.channel_appdata,
            &mut self.timing,
            channel_id,
            channel,
        );

        // Delete saved credential as it's no longer needed.
        {
            let mut aux = THP_AUX.try_lock().ok_or(CANNOT_UNLOCK)?;
            aux.delete_credential(channel_id);
        }

        Ok(old_channel_id)
    }

    // Keep the function in sync with insert_replace_lru.
    pub fn channel_close(&mut self, channel_id: u16) {
        // log::debug!("Closing {}", channel_id);
        let _was_closed = self.channel_appdata.remove(&channel_id).is_some()
            || self.channel_pairing.remove(&channel_id).is_some()
            || self.channel_opening.remove(&channel_id).is_some();
        self.timing.remove(&channel_id);

        // TODO credentials
        // XXX would be nice to clear sessions with this channel id (also
        // insert_replace_lru) only relevant to appdata channels
    }

    pub fn channel_close_all(&mut self) {
        self.channel_appdata.clear();
        self.channel_pairing.clear();
        self.channel_opening.clear();
        self.timing.clear();
        // TODO credential
        // TODO self.mux.reset();
    }

    pub fn channel_update_last_usage(&mut self, channel_id: u16) {
        if let Some(t) = self.timing.get_mut(&channel_id) {
            self.last_usage_counter = self.last_usage_counter.wrapping_add(1);
            t.update_last_usage(self.last_usage_counter);
        }
    }

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
            // log::debug!("cid:{} retry:{} ms:{}", channel_id, retry,
            // timeout_ms.unwrap_or(9999));
            earliest = match (earliest, timeout_ms) {
                // No result yet - update.
                (None, Some(t)) => Some((channel_id, t)),
                // Earlier timeout - update.
                (Some((_, t1)), Some(t2)) if t2 < t1 => Some((channel_id, t2)),
                // Otherwise keep the current best.
                _ => earliest,
            }
        }
        Ok(earliest)
    }

    pub fn send_device_locked(&mut self) -> Result<(), Error> {
        for ch in self.channel_opening.values_mut() {
            if ch.static_key_required() {
                ch.send_device_locked()?;
                // Channel will be closed after the error is sent out.
            }
        }
        Ok(())
    }

    pub fn send_transport_busy(&mut self, channel_id: u16) -> Result<(), Error> {
        let channel = self.lookup_channel_mut(channel_id)?;
        channel.send_error(TransportError::TransportBusy);
        Ok(())
    }

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

    /// Look up channel in `channel_appdata` and `channel_pairing` by its id.
    fn lookup_channel_mut(&mut self, channel_id: u16) -> Result<&mut TrezorChannel, Error> {
        self.channel_appdata
            .iter_mut()
            .chain(self.channel_pairing.iter_mut())
            .find(|&(cid, _)| cid == &channel_id)
            .map(|(_, ch)| ch)
            .ok_or(CHANNEL_NOT_FOUND)
    }

    /// Look up channel in `channel_appdata` and `channel_pairing` by its id.
    fn lookup_channel(&self, channel_id: u16) -> Result<&TrezorChannel, Error> {
        self.channel_appdata
            .iter()
            .chain(self.channel_pairing.iter())
            .find(|&(cid, _)| cid == &channel_id)
            .map(|(_, ch)| ch)
            .ok_or(CHANNEL_NOT_FOUND)
    }

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

    fn insert_replace_lru<T>(
        channels: &mut LinearMapView<u16, T>,
        timing: &mut LinearMapView<u16, ChannelTiming>,
        channel_id: u16,
        channel: T,
    ) {
        // Evict the oldest channel if we're out of slots.
        if channels.is_full() {
            let lru_cid = unwrap!(Self::least_recently_used(channels, timing,));
            channels.remove(&lru_cid);
            timing.remove(&lru_cid);
            // TODO if we closed a channel we should clear its sessions too
        }
        let res = channels.insert(channel_id, channel);
        let res = unwrap!(res); // should not happen since we deleted an entry if full
        assert!(res.is_none()); // id collisions not expected
    }

    fn get_channel_id(interfaces: &LinearMap<u8, InterfaceContext, MAX_INTERFACES>) -> u16 {
        let mut existing_cids = Vec::<u16, { MAX_INTERFACES * MAX_CHANNELS_ANY }>::new();
        for ifctx in interfaces.values() {
            existing_cids.extend(ifctx.channel_appdata.keys().copied());
            existing_cids.extend(ifctx.channel_pairing.keys().copied());
            existing_cids.extend(ifctx.channel_opening.keys().copied());
        }
        let mut result = CHANNEL_ID_COUNTER.get();
        while existing_cids.contains(&result) {
            result = CHANNEL_ID_COUNTER.get();
        }
        result
    }
}

#[derive(Clone)]
pub struct TrezorCredentialVerifier {
    iface_num: u8,
    channel_id: u16,
    device_properties: Vec<u8, MAX_DEVICE_PROPERTIES_LEN>,
    /// Micropython credential verification function. It is set just before it's
    /// needed to avoid holding long-lived reference to micropython memory
    /// in a global variable.
    verify_fn: Obj,
}

// Required by spin::Mutex to be able to lock verify_fn.
// SAFETY: We are in a single-threaded environment.
unsafe impl Send for TrezorCredentialVerifier {}

impl TrezorCredentialVerifier {
    fn new(
        iface_num: u8,
        channel_id: u16,
        device_properties: Vec<u8, MAX_DEVICE_PROPERTIES_LEN>,
    ) -> Self {
        Self {
            iface_num,
            channel_id,
            device_properties,
            verify_fn: Obj::const_none(),
        }
    }
}

impl CredentialVerifier for TrezorCredentialVerifier {
    fn verify(&self, remote_static_pubkey: &[u8], credential: &[u8]) -> PairingState {
        // log::debug!("TrezorCredentialVerifier::verify");
        let func = || -> Result<PairingState, Error> {
            if self.verify_fn == Obj::const_none()
                || credential.is_empty()
                || remote_static_pubkey.is_empty()
            {
                // log::debug!("Credential or verification function missing.")
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
        /*
        match res {
            Ok(ps) => log::debug!("Result: {}", ps as u8),
            Err(e) => log::error!("Error: {:?}", e),
        }
        */
        res.unwrap_or(PairingState::Unpaired)
    }

    fn device_properties(&self) -> &[u8] {
        self.device_properties.as_slice()
    }
}

enum TrezorInResult {
    None,
    Route(u16), // TODO buffer size
    Failed,
    KeyRequired(bool),
    MessageReady,
    MessageReadyAck,
    Ack,
    ChannelAllocation,
}

struct Auxiliary {
    host_keys: Vec<PubKey, MAX_CHANNELS_APPDATA>,
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
            // log::error!("Credential too long: {}", credential.len());
            return;
        };
        if self.credentials.is_full() {
            self.credentials.pop_front();
        }
        unwrap!(self.credentials.push_back((channel_id, credential)));
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

    pub fn host_keys_copy_from(&mut self, channels: &LinearMapView<u16, TrezorChannel>) {
        self.host_keys.clear();
        self.host_keys
            .extend(channels.values().map(|ch| *ch.remote_static_key()));
    }

    pub fn host_keys_contain(&self, host_key: &[u8]) -> bool {
        match host_key.try_into() {
            Ok(hk) => self.host_keys.contains(hk),
            _ => false,
        }
    }
}
