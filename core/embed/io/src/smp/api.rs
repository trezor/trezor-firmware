use rtl::CSlice;
use rtl::error::unwrap;

use super::{echo, image_info, process_rx_byte, reset, upload};

/// Send an SMP Echo request with a small text payload.
///
/// # Arguments
/// * `text` - Pointer to ASCII data that is not null-terminated.
/// * `text_len` - Number of bytes to send.
///
/// # Returns
/// `true` on successful send and valid response, `false` otherwise.
///
/// # Note
/// Length is bounded by the underlying SMP MTU; oversized input fails.
///
/// # Safety
/// `text` must point to `text_len` readable bytes.
#[unsafe(no_mangle)]
unsafe extern "C" fn smp_echo(text: *const cty::c_char, text_len: u8) -> bool {
    // SAFETY: caller must provide a valid pointer + length
    let text = unsafe { CSlice::from_ptr_and_len(text, text_len as usize) };
    echo::send(unwrap!(text.as_ascii_str()))
}

/// Issue an SMP Reset request to the remote nRF device.
///
/// Sends a reset command and does not wait for the device to come back.
#[unsafe(no_mangle)]
extern "C" fn smp_reset() {
    reset::send();
}

/// Parsed nRF application version in format
/// `"major.minor.revision[.build_num]"`.
///
/// Matches the MCUboot image header layout (8 bytes total).
/// If the optional build number is absent, it defaults to 0.
#[repr(C, packed)]
pub struct NrfAppVersion {
    /// Major version
    pub major: u8,
    /// Minor version
    pub minor: u8,
    /// Revision
    pub revision: u16,
    /// Optional build number
    pub build_num: u32,
}

/// Get the nRF app version as parsed integer components.
///
/// Sends an SMP request to the nRF device to retrieve the active application
/// image version, then parses the version string into individual numeric
/// components.
///
/// The accepted format is `"major.minor.revision[.build_num]"`, matching the
/// MCUboot image header layout. If the optional build number is absent, it
/// defaults to 0.
///
/// # Arguments
/// * `out` - Valid writable pointer to an `nrf_app_version_t` structure.
///
/// # Returns
/// `true` if version was successfully retrieved and parsed, `false` otherwise.
///
/// # Warning
/// Fails if the SMP channel cannot be acquired or the version format is
/// invalid.
#[unsafe(no_mangle)]
extern "C" fn smp_image_version_get(out: *mut NrfAppVersion) -> bool {
    if out.is_null() {
        return false;
    }
    match image_info::get_version_numbers() {
        Some(v) => {
            unsafe {
                (*out).major = v.major;
                (*out).minor = v.minor;
                (*out).revision = v.revision;
                (*out).build_num = v.build_num;
            }
            true
        }
        None => false,
    }
}

/// Upload an MCUboot image to the nRF device over SMP.
///
/// Streams the binary image followed by hash metadata, if required, using SMP
/// upload semantics.
///
/// # Arguments
/// * `data` - Pointer to the image buffer.
/// * `len` - Size of the image buffer in bytes.
/// * `image_hash` - Pointer to hash bytes; may be null if not used.
/// * `image_hash_len` - Length of the hash (for example, 32 for SHA-256).
/// * `progress` - Optional progress callback; `None` disables reporting.
///
/// # Returns
/// `true` if the upload completed successfully, `false` on error.
///
/// # Note
/// The caller must ensure the image fits the partition and the hash matches
/// the expected size.
///
/// # Safety
/// `data` must point to `len` readable bytes. If `image_hash_len` is nonzero,
/// `image_hash` must point to that many readable bytes.
#[unsafe(no_mangle)]
unsafe extern "C" fn smp_upload_app_image(
    data: *const cty::uint8_t,
    len: cty::size_t,
    image_hash: *const cty::uint8_t,
    image_hash_len: cty::size_t,
    progress: Option<extern "C" fn(cty::uint32_t, cty::uint32_t)>,
) -> bool {
    // SAFETY: caller must provide valid pointers + lengths
    let data = unsafe { CSlice::from_ptr_and_len(data, len) };
    let image_hash = unsafe { CSlice::from_ptr_and_len(image_hash, image_hash_len) };

    upload::upload_image(data.as_slice(), image_hash.as_slice(), progress)
}

/// Feed a received transport byte into the SMP RX state machine.
///
/// Call for each byte arriving from the nRF link (for example, UART). Assembles
/// frames and dispatches completed SMP responses internally.
///
/// # Arguments
/// * `byte` - Received raw byte.
#[unsafe(no_mangle)]
extern "C" fn smp_process_rx_byte(byte: u8) {
    process_rx_byte(byte)
}
