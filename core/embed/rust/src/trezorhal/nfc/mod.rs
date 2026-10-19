mod apdu;
mod error;
#[cfg(feature = "micropython")]
mod micropython;

use core::mem::MaybeUninit;
use core::sync::atomic::{AtomicU32, Ordering};

use apdu::{Apdu, CApdu, Instruction, RApdu, StatusWord};
use crypto::noise_xxpsk3::{NoiseXXpsk3, NoiseXXpsk3Ctx, DHLEN};
pub use error::NfcError;
use sys::time::ticks_ms;
use sys::ulog;

use super::{ffi, random};
use crate::strutil::{hex_bytes, strip_ok};
use crate::ui::event::NfcEvent;

pub const MAX_PIN_LEN: usize = 32;
pub const MAX_CERT_LEN: usize = RApdu::MAX_DATA_LEN;

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
    let mut r_apdu = RApdu::zero();
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

// TODO validate allowed characters?
fn encode_pin(pin: &str) -> Result<[u8; MAX_PIN_LEN], NfcError> {
    let mut res = [0xff; MAX_PIN_LEN];
    let pin = pin.as_bytes();
    res.get_mut(..pin.len())
        .ok_or(NfcError::InvalidData)?
        .copy_from_slice(pin);
    Ok(res)
}

enum TapState {
    Init,
    SentSelectApplet,
    SentHandshakePsk,
    SentHandshake1,
    SentHandshake2,
    SentPin,
    Ready,
    // Failed?
}

pub struct NoiseKeyPair<'a> {
    pub private: &'a [u8; DHLEN],
    pub public: &'a [u8; DHLEN],
}

struct TapContext<'a> {
    state: TapState,
    info: TagInfo,
    // `noise` borrows `noise_ctx`, so it must be declared (and dropped) first.
    // The struct must not be moved while `noise` is `Some`.
    noise: Option<NoiseXXpsk3<&'a mut NoiseXXpsk3Ctx>>,
    noise_ctx: NoiseXXpsk3Ctx,
    psk: [u8; NOISE_PSK_LEN],
    // for decryption & psk, probably better than on stack
    response_buf: Apdu,
}

impl<'a> TapContext<'a> {
    fn new(info: TagInfo) -> Self {
        Self {
            state: TapState::Init,
            info,
            noise: None,
            noise_ctx: NoiseXXpsk3Ctx::default(),
            psk: [0u8; _],
            response_buf: Apdu::zero(),
        }
    }

    pub fn get() -> Result<Self, NfcError> {
        let info = TagInfo::get()?;
        Ok(Self::new(info))
    }

    pub fn setup(
        &mut self,
        local_static_keys: Option<NoiseKeyPair<'_>>,
        pin: Option<&str>,
        verify_fn: &mut dyn FnMut(&[u8; DHLEN], &[u8]) -> bool,
    ) -> Result<bool, NfcError> {
        let next_state = match self.state {
            TapState::Init => self.handle_init()?,
            TapState::SentSelectApplet => {
                self.handle_sent_select_applet(local_static_keys.is_some())?
            }
            TapState::SentHandshakePsk => self.handle_sent_handshake_psk()?,
            TapState::SentHandshake1 => self.handle_sent_handshake1(
                local_static_keys.ok_or(NfcError::InvalidData)?,
                verify_fn,
            )?,
            TapState::SentHandshake2 => self.handle_sent_handshake2(pin)?,
            TapState::SentPin => self.handle_sent_pin()?,
            TapState::Ready => {
                ulog::error!("Tag connection already setup.");
                return Err(NfcError::InvalidData);
            }
        };
        self.state = next_state;
        Ok(matches!(self.state, TapState::Ready))
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

    fn handle_sent_select_applet(&mut self, secure_channel: bool) -> Result<TapState, NfcError> {
        transceive_complete()?.response_nodata()?;
        if !secure_channel {
            // TODO: don't need to select applet when there's no handshake
            ulog::debug!("No keys, setup done.");
            return Ok(TapState::Ready);
        }
        self.response_buf.write_with(|d: &mut [u8]| {
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
        // TODO: can we avoid psk struct member?
        self.psk = combine_psk_shares(trezor_share, card_share)?;
        // drop any previous borrow of noise_ctx before resetting it
        self.noise = None;
        self.noise_ctx = NoiseXXpsk3Ctx::default();
        // SAFETY: self-referential borrow. `noise_ctx` is only accessed through
        // `noise` from now on, `noise` is dropped before `noise_ctx` (field
        // order), and TapContext is not moved while `noise` is `Some`.
        let noise_ctx: &'a mut NoiseXXpsk3Ctx = unsafe { &mut *(&raw mut self.noise_ctx) };
        let noise = self
            .noise
            .insert(NoiseXXpsk3::new(noise_ctx).map_err(|_| NfcError::CryptoError)?);
        self.response_buf.write_with(|d: &mut [u8]| {
            noise
                .create_request1(&[], d)
                .map_err(|_| NfcError::CryptoError)
        })?;
        let c_apdu = CApdu::compose(Instruction::Handshake, self.response_buf.as_slice())?;
        transceive_start(&c_apdu)?;
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
        let noise = unwrap!(self.noise.as_mut());
        self.response_buf.write_with(|d: &mut [u8]| {
            noise
                .handle_response1(response, &mut remote_static_public_key, d)
                .map_err(|_| NfcError::CryptoError)
        })?;

        if !verify_fn(&remote_static_public_key, self.response_buf.as_slice()) {
            ulog::error!(
                "Certificate ({} B) validation failed.",
                self.response_buf.len()
            );
            return Err(NfcError::InvalidCertificate);
        }
        self.response_buf.write_with(|d: &mut [u8]| {
            noise
                .create_request2(
                    local_static_keys.private,
                    local_static_keys.public,
                    &self.psk,
                    &[],
                    d,
                )
                .map_err(|_| NfcError::CryptoError)
        })?;
        // TODO wipe keys
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
        let encoded_pin = match pin {
            None => return Ok(TapState::Ready),
            Some(pin) => encode_pin(pin)?,
        };
        let c_apdu = unwrap!(CApdu::compose(Instruction::Authenticate, &encoded_pin));
        self.send(&c_apdu)?;
        Ok(TapState::SentPin)
    }

    fn handle_sent_pin(&mut self) -> Result<TapState, NfcError> {
        let plaintext = self.receive()?;
        assert!(plaintext.len() == 0);
        ulog::debug!("PIN auth OK.");
        Ok(TapState::Ready)
    }

    pub fn command(&mut self, ins: Instruction, data: &[u8]) -> Result<(), NfcError> {
        // TODO check state maybe
        let c_apdu = CApdu::compose(ins, &data)?;
        self.send(&c_apdu)?;
        Ok(())
    }

    pub fn response(&mut self) -> Result<Option<&[u8]>, NfcError> {
        let payload = self.receive()?;
        if payload.len() > 0 {
            Ok(Some(payload))
        } else {
            Ok(None)
        }
    }

    fn receive(&mut self) -> Result<&[u8], NfcError> {
        let r_apdu = transceive_complete()?;
        let (data, code) = r_apdu.response()?;
        match self.noise.as_mut() {
            Some(noise) => {
                self.response_buf.write_with(|d: &mut [u8]| {
                    noise
                        .receive_message(data, d)
                        .map_err(|_| NfcError::CryptoError)
                })?; // XXX return code instead of CryptoError if != 9000?
                ulog::debug!(
                    "Transceive complete (len={}): {}.",
                    self.response_buf.len(),
                    hex_bytes(self.response_buf.as_slice())
                );
                if code != u16::from(StatusWord::Success) {
                    return Err(NfcError::CommandFailed(code));
                }
            }
            None => {
                if code != u16::from(StatusWord::Success) {
                    return Err(NfcError::CommandFailed(code));
                }
                self.response_buf.write_with(|d: &mut [u8]| {
                    let l = data.len();
                    d[..l].copy_from_slice(data);
                    Ok(l)
                })?;
            }
        }
        Ok(self.response_buf.as_slice())
    }

    fn send(&mut self, c_apdu: &CApdu) -> Result<(), NfcError> {
        match self.noise.as_mut() {
            Some(noise) => {
                ulog::debug!(
                    "Transceive start (len={}): {:?} {}.",
                    c_apdu.len(),
                    strip_ok(&c_apdu.ins()),
                    hex_bytes(c_apdu.as_slice())
                );
                self.response_buf.write_with(|d: &mut [u8]| {
                    noise
                        .send_message(c_apdu.as_slice(), d)
                        .map_err(|_| NfcError::CryptoError)
                })?;
                transceive_start(&self.response_buf)?;
            }
            None => {
                // TODO: assert instruction doesn't require secure channel
                transceive_start(c_apdu)?;
            }
        }
        Ok(())
    }
}
