mod apdu;
#[cfg(feature = "micropython")]
mod micropython;

use core::ffi::CStr;
use core::mem::MaybeUninit;

use apdu::{Apdu, Instruction, StatusWord};
use crypto::noise_xxpsk3::{NoiseXXpsk3, NoiseXXpsk3Ctx, DHLEN};
use heapless::{String, Vec};
use sys::time::Duration;
use sys::ulog;

use super::ffi;
use super::ffi::{StatusError};
use super::sysevent::{sysevents_poll, Syshandle};
use crate::time::Stopwatch;
use crate::ui::component::Event;
use crate::ui::event::NfcEvent;
use crate::strutil::hex_bytes;

pub const MAX_PIN_LEN: usize = 32;
pub const MAX_CERT_LEN: usize = Apdu::MAX_RESPONSE_DATA_LEN;

pub enum NfcError {
    DriverError(StatusError),
    InvalidData,
    TimedOut,
    UnsupportedTag,
    CommandFailed(StatusWord),
    CommandFailedUnknown(u16),
    HandshakeFailed,
}

impl From<StatusError> for NfcError {
    fn from(status: StatusError) -> Self {
        ulog::error!("NFC status not OK: {}", status.code);
        NfcError::DriverError(status)
    }
}

pub type DeviceInfo = ffi::nfc_dev_info_t; // XXX or CardInfo/TagInfo?

impl DeviceInfo {
    pub fn get() -> Result<Self, NfcError> {
        let mut dev_info = MaybeUninit::zeroed();
        unsafe {
            let res = ffi::nfc_get_device_info(dev_info.as_mut_ptr());
            res.ok()?;
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

    pub fn uid(&self) -> Result<&str, NfcError> {
        let p = unsafe { CStr::from_ptr(&self.uid as _) };
        p.to_str().map_err(|_| NfcError::InvalidData)
    }
    //TODO: uid
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
        _ => panic!(),
    }
}

pub fn start_discovery() -> Result<(), NfcError> {
    // SAFETY: ffi
    let res = unsafe { ffi::nfc_start_discovery() };
    res.ok()?;
    ulog::debug!("Started discovery.");
    Ok(())
}

pub fn stop_discovery() -> Result<(), NfcError> {
    // SAFETY: ffi
    let res = unsafe { ffi::nfc_stop_discovery() };
    res.ok()?;
    ulog::debug!("Stopped discovery.");
    Ok(())
}

pub fn is_connected() -> bool {
    unsafe { ffi::nfc_get_state() }
}

pub fn transceive(command: &Apdu) -> Result<Apdu, NfcError> {
    let mut response = Apdu::zero();
    ulog::debug!("Transceive command: {}.", hex_bytes(command));
    let status = unsafe { ffi::nfc_transceive(command as *const _, &mut response as *mut _) };
    status.ok()?;
    ulog::debug!("Transceive response: {}.", hex_bytes(&response));
    Ok(response)
}

pub const NOISE_PSK_SHARE_LEN: usize = 16;
pub const NOISE_PSK_LEN: usize = 32;

pub fn transceive_psk(
    trezor_share: &[u8; NOISE_PSK_SHARE_LEN],
) -> Result<[u8; NOISE_PSK_LEN], NfcError> {
    let mut result = [0u8; NOISE_PSK_LEN];
    let out = &mut result[NOISE_PSK_SHARE_LEN..];
    let mut out_size: u16 = 0;
    // SAFETY: ffi
    let status = unsafe {
        ffi::nfc_transceive_psk(
            trezor_share.as_ptr(),
            trezor_share.len(),
            out.as_mut_ptr(),
            out.len(),
            &mut out_size as *mut _,
        )
    };
    status.ok()?;
    if usize::from(out_size) != NOISE_PSK_SHARE_LEN {
        return Err(NfcError::InvalidData);
    }
    result[..NOISE_PSK_SHARE_LEN].copy_from_slice(trezor_share);
    Ok(result)
}

struct DiscoGuard {}

impl DiscoGuard {
    fn new() -> Result<Self, NfcError> {
        // XXX flush events?
        start_discovery()?;
        Ok(Self {})
    }

    fn wait_for_tap(&self) -> Result<(), NfcError> {
        let watch = Stopwatch::new_started();

        /*
        if is_connected() {
            ulog::warn!("Tap: already connected.");
            return Ok(())
        }
        */

        // TODO check is_connected if not flushing events?
        ulog::debug!("Wait for tap.");
        while watch.is_running_within(Duration::from_secs(10)) {
            let ev = sysevents_poll(&[Syshandle::Nfc]);
            match ev {
                None => {
                    ulog::debug!("Poll timeout.");
                }
                Some(Event::NFC(NfcEvent::Connected)) => {
                    ulog::debug!("Event: connected.");
                    if is_connected() {
                        ulog::debug!("Tap: connected.");
                        return Ok(());
                    }
                    ulog::error!("Event mismatch?");
                }
                Some(Event::NFC(NfcEvent::Disconnected)) => {
                    ulog::debug!("Event: disconnected.");
                }
                _ => {
                    ulog::error!("Unexpected event.");
                }
            }
        }

        ulog::error!("Timed out waiting for tap.");
        Err(NfcError::TimedOut)
    }
}

impl Drop for DiscoGuard {
    fn drop(&mut self) {
        if stop_discovery().is_err() {
            ulog::error!("Failed to stop discovery.");
        }
    }
}

const STATIC_PRIVATE_KEY: [u8; 32] = [
    0x43, 0xa1, 0x7e, 0x8a, 0xad, 0x8b, 0xf5, 0xb0, 0x26, 0x12, 0xfe, 0x6d, 0xeb, 0x77, 0xcd, 0xc0,
    0x84, 0x59, 0xad, 0x05, 0xf4, 0xd6, 0xb7, 0x32, 0xc5, 0xb4, 0xa2, 0xe1, 0xbf, 0xec, 0x99, 0x7b,
];
const STATIC_PUBLIC_KEY: [u8; 32] = [
    0x8a, 0xd7, 0x10, 0xc4, 0xcd, 0xa6, 0x35, 0xf7, 0x3f, 0x06, 0x04, 0x99, 0x4f, 0x79, 0xbd, 0x19,
    0xe9, 0xba, 0xfa, 0x10, 0x9c, 0xef, 0xe4, 0x22, 0xdd, 0x60, 0x86, 0x63, 0xc2, 0xe1, 0xa4, 0x58,
];

pub fn tap(
    ins: Instruction,
    data: &[u8],
    handshake: bool,
    pin: Option<&str>,
) -> Result<(), NfcError> {
    let g = DiscoGuard::new()?;
    g.wait_for_tap()?;

    let info = DeviceInfo::get()?;
    ulog::info!("Card UID: {}", info.uid().unwrap_or("unknown"));
    info.check()?;

    if !handshake {
        let c_apdu = Apdu::compose(ins, 0, 0, data).unwrap();
        let r_apdu = transceive(&c_apdu)?;
        let data = r_apdu.response()?;
        if data.len() > 0 {
            ulog::info!(
                "Success ({}): {}",
                data.len(),
                hex_bytes(data)
            );
        } else {
            ulog::info!("Success (no data)");
        }
        return Ok(());
    }

    let select_applet =
        Apdu::compose(Instruction::Select, 0x04, 0x00, apdu::APPLET_TREZOR_KEEP).unwrap();
    transceive(&select_applet)?.response_nodata()?;

    let psk = transceive_psk(&[0u8; NOISE_PSK_SHARE_LEN])?;

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
    let r_apdu = transceive(&c_apdu)?;
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
    let r_apdu = transceive(&c_apdu)?;
    let response = r_apdu.response()?;
    let payload_len = noise
        .receive_message(response, &mut noise_buf)
        .map_err(|_| NfcError::HandshakeFailed)?;
    ulog::info!(
        "Card says: {}.",
        str::from_utf8(&noise_buf[..payload_len]).unwrap()
    );

    if let Some(pin) = pin {
        // TODO: validate allowed characters?
        let mut pin_padded = [0xff; MAX_PIN_LEN];
        pin_padded[..pin.len()].copy_from_slice(pin.as_bytes());
        let encrypted_len = noise
            .send_message(&pin_padded, &mut noise_buf)
            .map_err(|_| NfcError::HandshakeFailed)?;
        let c_apdu = Apdu::compose(
            Instruction::Authenticate,
            0x00,
            0x00,
            &noise_buf[..encrypted_len],
        )
        .unwrap();
        transceive(&c_apdu)?.response_nodata()?;
        ulog::debug!("PIN auth OK.")
    }

    let encrypted_len = noise
        .send_message(&data, &mut noise_buf)
        .map_err(|_| NfcError::HandshakeFailed)?;
    let c_apdu = Apdu::compose(ins, 0, 0, &noise_buf[..encrypted_len]).unwrap();
    let r_apdu = transceive(&c_apdu)?;
    let response_data = r_apdu.response()?;
    if response_data.len() > 0 {
        let payload_len = noise
            .receive_message(&response_data, &mut noise_buf)
            .map_err(|_| NfcError::HandshakeFailed)?;
        let decrypted_data = &noise_buf[..payload_len];
        ulog::info!(
            "Success ({}->{}): {}",
            response_data.len(),
            decrypted_data.len(),
            hex_bytes(decrypted_data),
        );
    } else {
        ulog::info!("Success (no data)");
    }

    Ok(())
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
