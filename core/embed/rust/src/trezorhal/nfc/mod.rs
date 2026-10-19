mod apdu;
mod error;
#[cfg(feature = "micropython")]
mod micropython;

use core::mem::MaybeUninit;
use core::ops::{Deref, DerefMut};
use core::sync::atomic::{AtomicU32, Ordering};

use apdu::{Apdu, CApdu, Instruction, RApdu, StatusWord};
use crypto::noise_xxpsk3::{NoiseXXpsk3, NoiseXXpsk3Ctx, DHLEN, TAG_SIZE};
pub use error::NfcError;
use sys::time::ticks_ms;
use sys::ulog;
use zeroize::Zeroizing;

use super::{ffi, random};
use crate::strutil::{hex_bytes, strip_ok};
use crate::ui::event::NfcEvent;

pub const MAX_PIN_LEN: usize = 32;

pub const NOISE_PSK_LEN: usize = 32;
pub const NOISE_PSK_SHARE_LEN: usize = 16;

static START_TIMESTAMP: AtomicU32 = AtomicU32::new(0);

pub type TagInfo = ffi::nfc_dev_info_t;

impl TagInfo {
    pub fn get() -> Result<Self, NfcError> {
        let mut dev_info = MaybeUninit::zeroed();
        unsafe {
            ffi::nfc_get_device_info(dev_info.as_mut_ptr()).ok()?;
            // SAFETY: We only assume_init after the C call returns a success.
            Ok(dev_info.assume_init())
        }
    }

    pub fn check(&self) -> Result<(), NfcError> {
        if self.type_ != ffi::nfc_dev_type_t_NFC_DEV_TYPE_A {
            return Err(NfcError::UnsupportedTag);
        }
        Ok(())
    }

    pub fn uid(&self) -> &[u8] {
        let len = usize::from(self.uid_len).min(self.uid.len());
        &self.uid[..len]
    }
}

pub fn nfc_get_event() -> Option<ffi::nfc_event_t> {
    let mut nfc_event = MaybeUninit::zeroed();
    unsafe {
        let event_available = ffi::nfc_get_event(nfc_event.as_mut_ptr());
        // SAFETY: We only assume_init after the C call returns a success.
        event_available.then_some(nfc_event.assume_init())
    }
}

pub fn nfc_parse_event(event: ffi::nfc_event_t) -> NfcEvent {
    match event {
        ffi::nfc_event_t_NFC_EVENT_CONNECTED => NfcEvent::Connected,
        ffi::nfc_event_t_NFC_EVENT_DISCONNECTED => NfcEvent::Disconnected,
        ffi::nfc_event_t_NFC_EVENT_TRANSCEIVE_DONE => NfcEvent::TransceiveDone,
        _ => panic!(),
    }
}

pub fn start_discovery() -> Result<(), NfcError> {
    // SAFETY: ffi
    unsafe { ffi::nfc_start_discovery() }.ok()?;
    ulog::debug!("Starting discovery (connected: {}).", is_connected());
    Ok(())
}

pub fn stop_discovery() -> Result<(), NfcError> {
    // SAFETY: ffi
    unsafe { ffi::nfc_stop_discovery() }.ok()?;
    ulog::debug!("Stopped discovery.");
    Ok(())
}

pub fn is_connected() -> bool {
    // SAFETY: ffi
    unsafe { ffi::nfc_get_state() }
}

/// Starts an asynchronous exchange with an ISO-DEP card. Poll
/// `Syshandle::Nfc` until `NfcEvent::TransceiveDone`, then call
/// `transceive_complete`.
pub fn transceive_start<'a>(command: impl Into<&'a Apdu>) -> Result<(), NfcError> {
    let command: &Apdu = command.into();
    ulog::debug!(
        "Transceive start (len={}): {}.",
        command.len(),
        hex_bytes(command.as_slice())
    );
    // SAFETY: ffi, the command is copied before the call returns
    unsafe { ffi::nfc_transceive_start(command.as_ptr()).ok()? };
    START_TIMESTAMP.store(ticks_ms(), Ordering::Relaxed);
    Ok(())
}

/// Returns the response of the exchange started by `transceive_start`.
pub fn transceive_complete() -> Result<RApdu, NfcError> {
    let mut r_apdu = RApdu::default();
    // SAFETY: ffi
    unsafe { ffi::nfc_transceive_complete(r_apdu.as_mut_ptr()).ok()? };
    let len = r_apdu.len();
    let sw = r_apdu
        .sw()
        .and_then(|n| n.try_into().map_err(|_| NfcError::InvalidData));
    let hex = hex_bytes(&r_apdu);
    let duration_ms = ticks_ms().saturating_sub(START_TIMESTAMP.load(Ordering::Relaxed));
    match sw {
        Ok(StatusWord::Success) => ulog::debug!(
            "Transceive complete ({} ms, len={}): {}.",
            duration_ms,
            len,
            hex
        ),
        sw => ulog::error!(
            "Transceive complete ({} ms, len={}): {:?} {}.",
            duration_ms,
            len,
            strip_ok(&sw),
            hex
        ),
    };
    Ok(r_apdu)
}

/// Starts an asynchronous PSK exchange. Finish it like `transceive_start`.
pub fn transceive_psk_start(trezor_share: &[u8]) -> Result<(), NfcError> {
    ulog::debug!("Transceive PSK start.");
    // SAFETY: ffi, the share is copied before the call returns
    unsafe { ffi::nfc_transceive_psk_start(trezor_share.as_ptr(), trezor_share.len()).ok()? };
    Ok(())
}

fn combine_psk_shares(
    trezor_share: &[u8],
    card_share: &[u8],
) -> Result<[u8; NOISE_PSK_LEN], NfcError> {
    if trezor_share.len() != NOISE_PSK_SHARE_LEN || card_share.len() != NOISE_PSK_SHARE_LEN {
        return Err(NfcError::InvalidData);
    }
    let mut result = [0u8; NOISE_PSK_LEN];
    result[..NOISE_PSK_SHARE_LEN].copy_from_slice(trezor_share);
    result[NOISE_PSK_SHARE_LEN..].copy_from_slice(card_share);
    Ok(result)
}

fn encode_pin(pin: &str) -> Result<[u8; MAX_PIN_LEN], NfcError> {
    let mut res = [0xff; MAX_PIN_LEN];
    let pin = pin.as_bytes();
    res.get_mut(..pin.len())
        .ok_or(NfcError::UnexpectedInput)?
        .copy_from_slice(pin);
    Ok(res)
}

enum TapState {
    /// Tag active, handshake not started. Ready to send commands that don't
    /// require secure channel.
    Unsecured,
    /// Handshake: select applet.
    SentSelectApplet,
    /// Handshake: sent PSK.
    SentHandshakePsk,
    /// Handshake: sent handshake1
    SentHandshake1,
    /// Handshake: sent handshake2, may continue to SentPinUnlocked or
    /// SentAuthenticate or Secured depending on PIN.
    SentHandshake2,
    /// Handshake complete, caller requests authenticated channel with empty
    /// PIN, sent PinUnlocked to verify that it is indeed unset without
    /// incrementing PIN counter.
    SentPinUnlocked,
    /// Handshake complete, sent Authenticate. State skipped if no PIN provided.
    SentAuthenticate,
    /// Secure channel established, ready to send command.
    Secured,
    /// Communication failed.
    Failed,
}

pub struct NoiseKeyPair<'a> {
    pub private: &'a [u8; DHLEN],
    pub public: &'a [u8; DHLEN],
}

/// Session with a connected NFC tag.
struct TapContext<D: DerefMut<Target = NoiseXXpsk3Ctx>> {
    state: TapState,
    info: TagInfo,
    noise: NoiseXXpsk3<D>,
    // Buffer for encryption/decryption (we don't have in-place functions) - we could use space on
    // the stack but due to the size it's probably safer to use the heap. Also used to store
    // PSK between `SentSelectApplet`, `SentHandshakePsk`, and `SentHandshake1`. Zeroed on drop
    // as it may contain plaintext seed/share.
    response_buf: Zeroizing<Apdu>,
}

impl<D: DerefMut<Target = NoiseXXpsk3Ctx>> TapContext<D> {
    fn new(info: TagInfo, noise: NoiseXXpsk3<D>) -> Self {
        Self {
            state: TapState::Unsecured,
            info,
            noise,
            response_buf: Zeroizing::<Apdu>::default(),
        }
    }

    pub fn get(noise: D) -> Result<Self, NfcError> {
        let info = TagInfo::get()?;
        let noise = NoiseXXpsk3::new(noise).map_err(|_| NfcError::CryptoError)?;
        Ok(Self::new(info, noise))
    }

    pub fn setup(
        &mut self,
        local_static_keys: Option<NoiseKeyPair<'_>>,
        pin: Option<&str>,
        verify_fn: &mut dyn FnMut(&[u8; DHLEN], &[u8]) -> bool,
    ) -> Result<bool, NfcError> {
        match self.setup_step(local_static_keys, pin, verify_fn) {
            Err(e) => {
                self.state = TapState::Failed;
                Err(e)
            }
            Ok(next_state) => {
                self.state = next_state;
                Ok(matches!(self.state, TapState::Secured))
            }
        }
    }

    fn setup_step(
        &mut self,
        local_static_keys: Option<NoiseKeyPair<'_>>,
        pin: Option<&str>,
        verify_fn: &mut dyn FnMut(&[u8; DHLEN], &[u8]) -> bool,
    ) -> Result<TapState, NfcError> {
        match self.state {
            TapState::Unsecured => self.handle_init(),
            TapState::SentSelectApplet => self.handle_sent_select_applet(),
            TapState::SentHandshakePsk => self.handle_sent_handshake_psk(),
            TapState::SentHandshake1 => self.handle_sent_handshake1(
                local_static_keys.ok_or(NfcError::UnexpectedInput)?,
                verify_fn,
            ),
            TapState::SentHandshake2 => self.handle_sent_handshake2(pin),
            TapState::SentPinUnlocked => self.handle_sent_pin_unlocked(),
            TapState::SentAuthenticate => self.handle_sent_authenticate(),
            TapState::Secured => {
                ulog::error!("Tag connection already setup.");
                Err(NfcError::UnexpectedInput)
            }
            TapState::Failed => Err(NfcError::UnexpectedInput),
        }
    }

    fn handle_init(&self) -> Result<TapState, NfcError> {
        let select_applet = unwrap!(CApdu::compose(
            Instruction::Select,
            apdu::APPLET_TREZOR_N1W1
        ))
        .with_param(0x04, 0x00);
        transceive_start(&select_applet)?;
        Ok(TapState::SentSelectApplet)
    }

    fn handle_sent_select_applet(&mut self) -> Result<TapState, NfcError> {
        transceive_complete()?.response_ok_nodata()?;
        self.response_buf.write_with(|d| {
            let x = unwrap!(d.first_chunk_mut::<NOISE_PSK_SHARE_LEN>());
            random::bytes(x);
            Ok(NOISE_PSK_SHARE_LEN)
        })?;
        transceive_psk_start(self.response_buf.as_slice())?;
        Ok(TapState::SentHandshakePsk)
    }

    fn handle_sent_handshake_psk(&mut self) -> Result<TapState, NfcError> {
        let r_apdu = transceive_complete()?;
        let card_share = r_apdu.as_slice();
        let trezor_share = &self.response_buf.as_slice()[..NOISE_PSK_SHARE_LEN];
        let psk = combine_psk_shares(trezor_share, card_share)?;
        self.response_buf.write_with(|dest| {
            self.noise
                .create_request1(&[], dest)
                .map_err(|_| NfcError::CryptoError)
        })?;
        let c_apdu = CApdu::compose(Instruction::Handshake, self.response_buf.as_slice())?;
        transceive_start(&c_apdu)?;
        self.response_buf.write_with(|dest| {
            dest[..NOISE_PSK_LEN].copy_from_slice(&psk);
            Ok(NOISE_PSK_LEN)
        })?;
        Ok(TapState::SentHandshake1)
    }

    fn handle_sent_handshake1(
        &mut self,
        local_static_keys: NoiseKeyPair,
        verify_fn: &mut dyn FnMut(&[u8; DHLEN], &[u8]) -> bool,
    ) -> Result<TapState, NfcError> {
        let r_apdu = transceive_complete()?;
        let response = r_apdu.response_ok()?;
        let mut remote_static_public_key = [0u8; DHLEN];
        let psk: [u8; NOISE_PSK_LEN] = self
            .response_buf
            .as_slice()
            .try_into()
            .map_err(|_| NfcError::UnexpectedInput)?;
        self.response_buf.write_with(|dest| {
            self.noise
                .handle_response1(response, &mut remote_static_public_key, dest)
                .map_err(|_| NfcError::CryptoError)
        })?;

        if !verify_fn(&remote_static_public_key, self.response_buf.as_slice()) {
            ulog::error!(
                "Certificate ({} B) validation failed.",
                self.response_buf.len()
            );
            return Err(NfcError::InvalidCertificate);
        }
        self.response_buf.write_with(|dest| {
            self.noise
                .create_request2(
                    local_static_keys.private,
                    local_static_keys.public,
                    &psk,
                    &[],
                    dest,
                )
                .map_err(|_| NfcError::CryptoError)
        })?;
        let c_apdu = unwrap!(CApdu::compose(
            Instruction::Handshake,
            self.response_buf.as_slice()
        ))
        .with_param(0x01, 0x00);
        transceive_start(&c_apdu)?;
        Ok(TapState::SentHandshake2)
    }

    fn handle_sent_handshake2(&mut self, pin: Option<&str>) -> Result<TapState, NfcError> {
        let payload = self.receive()?;
        ulog::debug!(
            "Handshake complete, tag says: {}.",
            str::from_utf8(payload).unwrap_or("[invalid UTF-8]")
        );
        match pin {
            None => Ok(TapState::Secured),
            Some("") => {
                let c_apdu = unwrap!(CApdu::compose(Instruction::PinUnlocked, &[]));
                self.send(&c_apdu)?;
                Ok(TapState::SentPinUnlocked)
            }
            Some(pin) => {
                let encoded_pin = encode_pin(pin)?;
                let c_apdu = unwrap!(CApdu::compose(Instruction::Authenticate, &encoded_pin));
                self.send(&c_apdu)?;
                Ok(TapState::SentAuthenticate)
            }
        }
    }

    fn handle_sent_pin_unlocked(&mut self) -> Result<TapState, NfcError> {
        let plaintext = self.receive()?;
        if !plaintext.is_empty() {
            log::error!("Expected empty response, got {} B.", plaintext.len());
            return Err(NfcError::InvalidData);
        }
        ulog::debug!("PIN is not set.");
        let encoded_pin = encode_pin("")?;
        let c_apdu = unwrap!(CApdu::compose(Instruction::Authenticate, &encoded_pin));
        self.send(&c_apdu)?;
        Ok(TapState::SentAuthenticate)
    }

    fn handle_sent_authenticate(&mut self) -> Result<TapState, NfcError> {
        let plaintext = self.receive()?;
        if !plaintext.is_empty() {
            log::error!("Expected empty response, got {} B.", plaintext.len());
            return Err(NfcError::InvalidData);
        }
        ulog::debug!("PIN auth OK.");
        Ok(TapState::Secured)
    }

    pub fn command(&mut self, ins: Instruction, data: &[u8]) -> Result<(), NfcError> {
        if !matches!(self.state, TapState::Unsecured | TapState::Secured) {
            return Err(NfcError::UnexpectedInput);
        }
        let c_apdu = CApdu::compose(ins, data)?;
        self.send(&c_apdu)?;
        Ok(())
    }

    pub fn response(&mut self) -> Result<Option<&[u8]>, NfcError> {
        if !matches!(self.state, TapState::Unsecured | TapState::Secured) {
            return Err(NfcError::UnexpectedInput);
        }
        let payload = self.receive()?;
        if !payload.is_empty() {
            Ok(Some(payload))
        } else {
            Ok(None)
        }
    }

    fn receive(&mut self) -> Result<&[u8], NfcError> {
        let r_apdu = transceive_complete()?;
        let (data, code) = r_apdu.response()?;
        if matches!(self.state, TapState::Unsecured) {
            if code != u16::from(StatusWord::Success) {
                return Err(NfcError::CommandFailed(code));
            }
            self.response_buf.write_with(|dest| {
                let l = data.len();
                dest[..l].copy_from_slice(data);
                Ok(l)
            })?;
        } else {
            // We need to decrypt first, then check the status code, otherwise the noise
            // counter doesn't get incremented and the secure channel breaks even if the
            // error wasn't fatal.
            let res = self.response_buf.write_with(|dest| {
                self.noise
                    .receive_message(data, dest)
                    .map_err(|_| NfcError::CryptoError)
            });
            if code != u16::from(StatusWord::Success) {
                return Err(NfcError::CommandFailed(code));
            }
            res?;
            ulog::debug!(
                "Transceive complete (len={}){}{}.",
                self.response_buf.len(),
                self.response_buf.is_empty().then_some("").unwrap_or(": "),
                hex_bytes(self.response_buf.as_slice())
            );
        };
        Ok(self.response_buf.as_slice())
    }

    fn send(&mut self, c_apdu: &CApdu) -> Result<(), NfcError> {
        if matches!(self.state, TapState::Unsecured) {
            if c_apdu.ins().is_ok_and(|i| i.needs_handshake()) {
                return Err(NfcError::UnexpectedInput);
            }
            transceive_start(c_apdu)?;
        } else {
            ulog::debug!(
                "Transceive start (len={}): {:?} {}.",
                c_apdu.len(),
                strip_ok(&c_apdu.ins()),
                hex_bytes(c_apdu.as_slice())
            );
            self.response_buf.write_with(|dest| {
                self.noise
                    .send_message(c_apdu.as_slice(), dest)
                    .map_err(|_| NfcError::CryptoError)
            })?;
            transceive_start(self.response_buf.deref())?;
        };
        Ok(())
    }
}
