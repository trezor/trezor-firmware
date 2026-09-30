mod apdu;
mod error;
#[cfg(feature = "micropython")]
mod micropython;

use core::mem::MaybeUninit;

use apdu::{Apdu, Instruction, StatusWord};
use crypto::noise_xxpsk3::{NoiseXXpsk3, NoiseXXpsk3Ctx, DHLEN};
pub use error::NfcError;
use heapless::{String, Vec};
use sys::time::Duration;
use sys::ulog;

use super::ffi;
use super::sysevent::{sysevents_poll, /* sysevents_poll_timeout, */ Syshandle};
use crate::strutil::hex_bytes;
use crate::time::Stopwatch;
use crate::ui::component::Event;
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
    /*
    // TODO: figure out why prodtest does this
    if nfc_get_event().is_some() {
        ulog::error!("Stale NFC event (connected: {}).", is_connected());
    }
    // TODO: figure out why prodtest does this
    if sysevents_poll_timeout(&[Syshandle::Nfc], Duration::ZERO).is_some() {
        ulog::error!("Stale NFC event 2 (connected: {}).", is_connected());
    }
    ulog::debug!("Started discovery."); */
    Ok(())
}

pub fn stop_discovery() -> Result<(), NfcError> {
    // SAFETY: ffi
    unsafe { ffi::nfc_stop_discovery() }.ok()?;
    ulog::debug!("Stopped discovery.");
    /*if sysevents_poll_timeout(&[Syshandle::Nfc], Duration::ZERO).is_some() {
        ulog::debug!("Stale NFC event in stop_discovery (connected: {}).", is_connected());
    }*/
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
            .unwrap_or(Instruction::ActivateFlashloader /* yeah */),
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

// TODO: delete
fn sysevents_wait_for(wanted_event: NfcEvent) -> Result<(), NfcError> {
    let watch = Stopwatch::new_started();

    while watch.is_running_within(Duration::from_secs(10)) {
        let ev = sysevents_poll(&[Syshandle::Nfc]);
        if ev == Some(Event::NFC(wanted_event)) {
            return Ok(());
        }
        match ev {
            None => ulog::debug!("Poll timeout."),
            Some(Event::NFC(ne)) => ulog::debug!("NFC: {:?}.", ne),
            Some(other) => ulog::debug!("Unexpected event {:?}.", other),
        }
    }
    ulog::error!("Timed out waiting for {:?}.", wanted_event);
    Err(NfcError::TimedOut)
}

struct DiscoGuard {}

impl Drop for DiscoGuard {
    fn drop(&mut self) {
        if stop_discovery().is_err() {
            ulog::error!("Failed to stop discovery.");
        }
    }
}

impl DiscoGuard {
    fn new() -> Result<Self, NfcError> {
        start_discovery()?;
        Ok(Self {})
    }

    fn wait_for_tap(&self) -> Result<(), NfcError> {
        ulog::debug!("Wait for tap.");
        if is_connected() {
            ulog::warning!("Tap: already connected.");
            //return Ok(()) // returning here & transceiving causes ENOSTATE
        }
        sysevents_wait_for(NfcEvent::Connected)?;
        assert!(is_connected());
        Ok(())
    }

    pub fn transceive_blocking(&self, command: &Apdu) -> Result<Apdu, NfcError> {
        transceive_start(command)?;
        sysevents_wait_for(NfcEvent::TransceiveDone)?;
        transceive_complete()
    }

    pub fn transceive_psk_blocking(
        &self,
        trezor_share: &[u8; NOISE_PSK_SHARE_LEN],
    ) -> Result<[u8; NOISE_PSK_LEN], NfcError> {
        transceive_psk_start(trezor_share)?;
        sysevents_wait_for(NfcEvent::TransceiveDone)?;
        let response = transceive_complete()?;
        let card_share = response.as_slice();
        if card_share.len() != NOISE_PSK_SHARE_LEN {
            return Err(NfcError::InvalidData);
        }
        let mut result = [0u8; NOISE_PSK_LEN];
        result[..NOISE_PSK_SHARE_LEN].copy_from_slice(trezor_share);
        result[NOISE_PSK_SHARE_LEN..].copy_from_slice(card_share);
        Ok(result)
    }
}

const STATIC_PRIVATE_KEY: [u8; DHLEN] = [
    0x43, 0xa1, 0x7e, 0x8a, 0xad, 0x8b, 0xf5, 0xb0, 0x26, 0x12, 0xfe, 0x6d, 0xeb, 0x77, 0xcd, 0xc0,
    0x84, 0x59, 0xad, 0x05, 0xf4, 0xd6, 0xb7, 0x32, 0xc5, 0xb4, 0xa2, 0xe1, 0xbf, 0xec, 0x99, 0x7b,
];
const STATIC_PUBLIC_KEY: [u8; DHLEN] = [
    0x8a, 0xd7, 0x10, 0xc4, 0xcd, 0xa6, 0x35, 0xf7, 0x3f, 0x06, 0x04, 0x99, 0x4f, 0x79, 0xbd, 0x19,
    0xe9, 0xba, 0xfa, 0x10, 0x9c, 0xef, 0xe4, 0x22, 0xdd, 0x60, 0x86, 0x63, 0xc2, 0xe1, 0xa4, 0x58,
];

fn encode_pin(pin: &str) -> Result<Vec<u8, MAX_PIN_LEN>, NfcError> {
    let mut res = Vec::new();
    res.extend_from_slice(pin.as_bytes())
        .map_err(|_| NfcError::InvalidData)?; // FIXME no
    unwrap!(res.resize(MAX_PIN_LEN, 0xff));
    Ok(res)
}

pub fn tap(ins: Instruction, data: &[u8]) -> Result<Vec<u8, 256>, NfcError> {
    let handshake = ins.needs_handshake();
    let pin = ins.needs_auth().then_some("");

    let g = DiscoGuard::new()?;
    g.wait_for_tap()?;

    let info = TagInfo::get()?;
    ulog::info!("Tag UID: {}", hex_bytes(info.uid()));
    info.check()?;

    if !handshake {
        let c_apdu = Apdu::compose(ins, 0, 0, data).unwrap();
        let r_apdu = g.transceive_blocking(&c_apdu)?;
        let data = r_apdu.response()?;
        if data.len() > 0 {
            ulog::info!("Success ({}): {}", data.len(), hex_bytes(data));
        } else {
            ulog::info!("Success (no data)");
        }
        return Ok(Vec::from_slice(data).unwrap());
    }

    let select_applet =
        Apdu::compose(Instruction::Select, 0x04, 0x00, apdu::APPLET_TREZOR_N1W1).unwrap();
    g.transceive_blocking(&select_applet)?.response_nodata()?;

    let psk = g.transceive_psk_blocking(&[0u8; NOISE_PSK_SHARE_LEN])?;

    let mut noise_buf = [0u8; 512];
    let mut ctx = NoiseXXpsk3Ctx::default();
    let mut noise = NoiseXXpsk3::new(&mut ctx, &psk, &STATIC_PRIVATE_KEY, &STATIC_PUBLIC_KEY)
        .map_err(|_| NfcError::HandshakeFailed)?;

    let request_len = noise
        .create_request1(&[], &mut noise_buf)
        .map_err(|_| NfcError::HandshakeFailed)?;
    let c_apdu = Apdu::compose(
        Instruction::Handshake,
        0x00,
        0x00,
        &noise_buf[..request_len],
    )
    .unwrap();
    let r_apdu = g.transceive_blocking(&c_apdu)?;
    let response = r_apdu.response()?;
    let mut remote_static_public_key = [0u8; 32];
    let payload_len = noise
        .handle_response1(response, &mut remote_static_public_key, &mut noise_buf)
        .map_err(|_| NfcError::HandshakeFailed)?;
    ulog::debug!("Got certificate: {} B.", payload_len);
    // TODO verify that pubkey matches the one in certificate

    let request_len = noise
        .create_request2(&[], &mut noise_buf)
        .map_err(|_| NfcError::HandshakeFailed)?;
    let c_apdu = Apdu::compose(
        Instruction::Handshake,
        0x01,
        0x00,
        &noise_buf[..request_len],
    )
    .unwrap();
    let r_apdu = g.transceive_blocking(&c_apdu)?;
    let response = r_apdu.response()?;
    let payload_len = noise
        .receive_message(response, &mut noise_buf)
        .map_err(|_| NfcError::HandshakeFailed)?;
    ulog::info!(
        "Tag says: {}.",
        str::from_utf8(&noise_buf[..payload_len]).unwrap()
    );

    if let Some(pin) = pin {
        // TODO: validate allowed characters?
        //let mut pin_padded = [0xff; MAX_PIN_LEN];
        //pin_padded[..pin.len()].copy_from_slice(pin.as_bytes());
        let pin_padded = encode_pin(pin)?;
        ulog::debug!("Pin: {}", hex_bytes(&pin_padded));
        let encrypted_len = noise
            .send_message(&pin_padded, &mut noise_buf)
            .map_err(|_| NfcError::HandshakeFailed)?;
        ulog::debug!(
            "Encrypted: ({}) {}",
            encrypted_len,
            hex_bytes(&noise_buf[..encrypted_len])
        );
        let c_apdu = Apdu::compose(
            Instruction::Authenticate,
            0x00,
            0x00,
            &noise_buf[..encrypted_len],
        )
        .unwrap();
        g.transceive_blocking(&c_apdu)?.response_nodata()?;
        ulog::debug!("PIN auth OK.")
    }

    let c_apdu = if ins.encrypted_data() {
        let encrypted_len = noise
            .send_message(&data, &mut noise_buf)
            .map_err(|_| NfcError::HandshakeFailed)?;
        Apdu::compose(ins, 0, 0, &noise_buf[..encrypted_len]).unwrap()
    } else {
        Apdu::compose(ins, 0, 0, &data).unwrap()
    };
    let r_apdu = g.transceive_blocking(&c_apdu)?;
    let response_data = r_apdu.response()?;
    let ret = if response_data.len() > 0 {
        let decrypted_data = if ins.encrypted_data() {
            let payload_len = noise
                .receive_message(&response_data, &mut noise_buf)
                .map_err(|_| NfcError::HandshakeFailed)?;
            &noise_buf[..payload_len]
        } else {
            &response_data
        };
        ulog::info!(
            "Success ({}->{}): {}",
            response_data.len(),
            decrypted_data.len(),
            hex_bytes(decrypted_data),
        );
        decrypted_data
    } else {
        ulog::info!("Success (no data)");
        &[]
    };

    Ok(Vec::from_slice(ret).unwrap())
}

enum TapState {
    Init,
    SelectApplet,
    HandshakePsk,
    Handshake1,
    Handshake2,
    Command,
}

struct TapContext {
    state: TapState,
    handshake_done: bool,
    auth_done: bool,
    // noise_state ...
    pin: Option<String<MAX_PIN_LEN>>,
    remote_static_public_key: [u8; DHLEN],
    certificate: Vec<u8, MAX_CERT_LEN>,
    current_command: Option<Apdu>,
}
// TODO context obj:
//  pin
//  noise state
//  certificate
