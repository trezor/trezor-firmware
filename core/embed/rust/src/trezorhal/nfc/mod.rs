mod apdu;
mod error;
#[cfg(feature = "micropython")]
mod micropython;

use core::mem::MaybeUninit;

use apdu::{Apdu, Instruction, StatusWord};
use crypto::noise_xxpsk3::{NoiseXXpsk3, NoiseXXpsk3Ctx, DHLEN};
pub use error::NfcError;
use sys::ulog;

use super::{ffi, random};
use crate::strutil::hex_bytes;
use crate::ui::event::NfcEvent;

pub const MAX_PIN_LEN: usize = 32;
pub const MAX_CERT_LEN: usize = Apdu::MAX_RESPONSE_DATA_LEN;

pub const NOISE_PSK_LEN: usize = 32;
pub const NOISE_PSK_SHARE_LEN: usize = 16;

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
pub fn transceive_start(command: &Apdu) -> Result<(), NfcError> {
    ulog::debug!(
        "Transceive start: {:?} {}.",
        command
            .ins()
            .unwrap_or(Instruction::ActivateFlashloader /* FIXME */),
        hex_bytes(command)
    );
    // SAFETY: ffi, the command is copied before the call returns
    unsafe { ffi::nfc_transceive_start(command as *const _).ok()? };
    Ok(())
}

/// Returns the response of the exchange started by `transceive_start`.
pub fn transceive_complete() -> Result<Apdu, NfcError> {
    let mut r_apdu = Apdu::zero();
    // SAFETY: ffi
    unsafe { ffi::nfc_transceive_complete(&mut r_apdu as *mut _).ok()? };
    match StatusWord::try_from(r_apdu.sw()?) {
        Err(()) => ulog::debug!("Transceive response: {}.", hex_bytes(&r_apdu)),
        Ok(sw) => ulog::debug!("Transceive response: {:?} {}.", sw, hex_bytes(&r_apdu)),
    };
    Ok(r_apdu)
}

/// Starts an asynchronous PSK exchange. Finish it like `transceive_start`.
pub fn transceive_psk_start(trezor_share: &[u8; NOISE_PSK_SHARE_LEN]) -> Result<(), NfcError> {
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

struct NoiseKeyPair {
    private: [u8; DHLEN],
    public: [u8; DHLEN],
}

struct TapContext<'a> {
    state: TapState,
    info: TagInfo,
    // `noise` borrows `noise_ctx`, so it must be declared (and dropped) first.
    // The struct must not be moved while `noise` is `Some`.
    noise: Option<NoiseXXpsk3<&'a mut NoiseXXpsk3Ctx>>,
    noise_ctx: NoiseXXpsk3Ctx,
    pin: Option<[u8; MAX_PIN_LEN]>,
    static_keys: Option<NoiseKeyPair>,
    decrypt_response: bool,
    max_response: u16,
    // for decryption & psk, probably better than on stack
    response_buf: [u8; Apdu::MAX_RESPONSE_DATA_LEN],
}

impl<'a> TapContext<'a> {
    fn new(info: TagInfo) -> Self {
        Self {
            state: TapState::Init,
            info,
            noise: None,
            noise_ctx: NoiseXXpsk3Ctx::default(),
            pin: None,
            static_keys: None,
            decrypt_response: false,
            max_response: 0,
            response_buf: [0; _],
        }
    }

    pub fn get() -> Result<Self, NfcError> {
        let info = TagInfo::get()?;
        Ok(Self::new(info))
    }

    pub fn set_keys(
        &mut self,
        static_private_key: &[u8],
        static_public_key: &[u8],
    ) -> Result<(), NfcError> {
        self.static_keys = Some(NoiseKeyPair {
            private: static_private_key
                .try_into()
                .map_err(|_| NfcError::InvalidData)?,
            public: static_public_key
                .try_into()
                .map_err(|_| NfcError::InvalidData)?,
        });
        Ok(())
    }

    pub fn set_pin(&mut self, pin: &str) -> Result<(), NfcError> {
        self.pin = Some(encode_pin(pin)?);
        Ok(())
    }

    pub fn setup(
        &mut self,
        verify_fn: &dyn Fn(&[u8; DHLEN], &[u8]) -> bool,
    ) -> Result<bool, NfcError> {
        let next_state = match self.state {
            TapState::Init => self.handle_init()?,
            TapState::SentSelectApplet => self.handle_sent_select_applet()?,
            TapState::SentHandshakePsk => self.handle_sent_handshake_psk()?,
            TapState::SentHandshake1 => self.handle_sent_handshake1(verify_fn)?,
            TapState::SentHandshake2 => self.handle_sent_handshake2()?,
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
        let select_applet = unwrap!(Apdu::compose(
            Instruction::Select,
            0x04,
            0x00,
            apdu::APPLET_TREZOR_N1W1
        ));
        transceive_start(&select_applet)?;
        Ok(TapState::SentSelectApplet)
    }

    fn handle_sent_select_applet(&mut self) -> Result<TapState, NfcError> {
        transceive_complete()?.response_nodata()?;
        if self.static_keys.is_none() {
            ulog::debug!("No keys, setup done.");
            return Ok(TapState::Ready);
        }
        let trezor_share = unwrap!(self.response_buf.first_chunk_mut::<NOISE_PSK_SHARE_LEN>());
        random::bytes(trezor_share);
        transceive_psk_start(trezor_share)?;
        Ok(TapState::SentHandshakePsk)
    }

    fn handle_sent_handshake_psk(&mut self) -> Result<TapState, NfcError> {
        let r_apdu = transceive_complete()?;
        let card_share = r_apdu.as_slice();
        let trezor_share = &self.response_buf[..NOISE_PSK_SHARE_LEN];
        let psk = combine_psk_shares(trezor_share, card_share)?;
        let static_keys = unwrap!(self.static_keys.as_ref());
        // drop any previous borrow of noise_ctx before resetting it
        self.noise = None;
        self.noise_ctx = NoiseXXpsk3Ctx::default();
        // SAFETY: self-referential borrow. `noise_ctx` is only accessed through
        // `noise` from now on, `noise` is dropped before `noise_ctx` (field
        // order), and TapContext is not moved while `noise` is `Some`.
        let noise_ctx: &'a mut NoiseXXpsk3Ctx = unsafe { &mut *(&raw mut self.noise_ctx) };
        let noise = self.noise.insert(
            NoiseXXpsk3::new(noise_ctx, &psk, &static_keys.private, &static_keys.public)
                .map_err(|_| NfcError::HandshakeFailed)?,
        );
        let request_len = noise
            .create_request1(&[], &mut self.response_buf)
            .map_err(|_| NfcError::HandshakeFailed)?;
        let c_apdu = unwrap!(Apdu::compose(
            Instruction::Handshake,
            0x00,
            0x00,
            &self.response_buf[..request_len],
        ));
        transceive_start(&c_apdu)?;
        Ok(TapState::SentHandshake1)
    }

    fn handle_sent_handshake1(
        &mut self,
        verify_fn: &dyn Fn(&[u8; DHLEN], &[u8]) -> bool,
    ) -> Result<TapState, NfcError> {
        let r_apdu = transceive_complete()?;
        let response = r_apdu.response()?;
        let mut remote_static_public_key = [0u8; DHLEN];
        let noise = unwrap!(self.noise.as_mut());
        let payload_len = noise
            .handle_response1(
                response,
                &mut remote_static_public_key,
                &mut self.response_buf,
            )
            .map_err(|_| NfcError::HandshakeFailed)?;
        let cert_ok = verify_fn(&remote_static_public_key, &self.response_buf[..payload_len]);
        ulog::debug!(
            "Got certificate ({} B), verification OK: {}.",
            payload_len,
            cert_ok
        );
        if !cert_ok {
            return Err(NfcError::HandshakeFailed);
        }
        let request_len = noise
            .create_request2(&[], &mut self.response_buf)
            .map_err(|_| NfcError::HandshakeFailed)?;
        let c_apdu = unwrap!(Apdu::compose(
            Instruction::Handshake,
            0x01,
            0x00,
            &self.response_buf[..request_len],
        ));
        transceive_start(&c_apdu)?;
        Ok(TapState::SentHandshake2)
    }

    fn handle_sent_handshake2(&mut self) -> Result<TapState, NfcError> {
        let r_apdu = transceive_complete()?;
        let response = r_apdu.response()?;
        let payload = self.noise_receive(response)?;
        ulog::debug!(
            "Handshake complete, tag says: {}.",
            str::from_utf8(payload).unwrap_or("[invalid UTF-8]")
        );
        let Some(pin) = self.pin else {
            return Ok(TapState::Ready);
        };
        let encrypted = self.noise_send(&pin)?;
        let c_apdu = unwrap!(Apdu::compose(
            Instruction::Authenticate,
            0x00,
            0x00,
            encrypted,
        ));
        transceive_start(&c_apdu)?;
        Ok(TapState::SentPin)
    }

    fn handle_sent_pin(&self) -> Result<TapState, NfcError> {
        transceive_complete()?.response_nodata()?;
        ulog::debug!("PIN auth OK.");
        Ok(TapState::Ready)
    }

    pub fn command(&mut self, ins: Instruction, data: &[u8]) -> Result<(), NfcError> {
        // TODO check state maybe
        let c_apdu = if ins.encrypted_data() {
            let encrypted = self.noise_send(&data)?;
            Apdu::compose(ins, 0, 0, encrypted).unwrap()
        } else {
            Apdu::compose(ins, 0, 0, &data).unwrap()
        };
        transceive_start(&c_apdu)?;
        self.decrypt_response = ins.encrypted_data();
        self.max_response = ins.max_expected_response();
        Ok(())
    }

    pub fn response(&mut self) -> Result<Option<&[u8]>, NfcError> {
        let r_apdu = transceive_complete()?;
        let response_data = r_apdu.response()?;
        if response_data.len() > 0 {
            let decrypted_data = if self.decrypt_response {
                self.noise_receive(&response_data)?
            } else {
                let dest = &mut self.response_buf[..response_data.len()];
                dest.copy_from_slice(response_data);
                dest
            };
            ulog::info!(
                "Success ({}->{}): {}",
                response_data.len(),
                decrypted_data.len(),
                hex_bytes(decrypted_data),
            );
            Ok(Some(decrypted_data))
        } else {
            ulog::info!("Success (no data)");
            Ok(None)
        }
    }

    fn noise_receive(&mut self, ciphertext: &[u8]) -> Result<&[u8], NfcError> {
        let noise = unwrap!(self.noise.as_mut());
        let payload_len = noise
            .receive_message(ciphertext, &mut self.response_buf)
            .map_err(|_| NfcError::HandshakeFailed)?;
        Ok(&self.response_buf[..payload_len])
    }

    fn noise_send(&mut self, plaintext: &[u8]) -> Result<&[u8], NfcError> {
        let noise = unwrap!(self.noise.as_mut());
        let payload_len = noise
            .send_message(plaintext, &mut self.response_buf)
            .map_err(|_| NfcError::HandshakeFailed)?;
        Ok(&self.response_buf[..payload_len])
    }

    // TODO use, rename response_buf as it's not just for responses
    fn clear_buf(&mut self) -> &mut [u8] {
        self.response_buf.fill(0);
        &mut self.response_buf
    }
}
