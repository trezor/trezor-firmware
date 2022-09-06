use crate::error::Error;

use cstr_core::CStr;

extern "C" {
    fn display_qrcode(
        x: cty::c_int,
        y: cty::c_int,
        data: *const cty::uint16_t,
        scale: cty::uint8_t,
    );
}

const NVERSIONS: usize = 10; // range of versions (=capacities) that we support
const QR_WIDTHS: [u32; NVERSIONS] = [21, 25, 29, 33, 37, 41, 45, 49, 53, 57];
const THRESHOLDS_BINARY: [usize; NVERSIONS] = [14, 26, 42, 62, 84, 106, 122, 152, 180, 213];
const THRESHOLDS_ALPHANUM: [usize; NVERSIONS] = [20, 38, 61, 90, 122, 154, 178, 221, 262, 311];
const ALPHANUM: &str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $*+-./:";

const MAX_DATA: usize = THRESHOLDS_ALPHANUM[THRESHOLDS_ALPHANUM.len() - 1] + 1; //FIXME

fn is_alphanum_only(data: &str) -> bool {
    data.chars().all(|c| ALPHANUM.contains(c))
}

fn qr_version_index(data: &str, thresholds: &[usize]) -> Option<usize> {
    for (i, threshold) in thresholds.iter().enumerate() {
        if data.len() <= *threshold {
            return Some(i);
        }
    }
    None
}

pub fn render_qrcode(
    x: i16,
    y: i16,
    data: &str,
    max_size: u32,
    case_sensitive: bool,
) -> Result<(), Error> {
    let data_len = data.len();
    let version_idx;
    let mut buffer = [0u8; MAX_DATA];
    assert!(data_len < buffer.len());
    buffer.as_mut_slice()[..data_len].copy_from_slice(data.as_bytes());

    if case_sensitive && !is_alphanum_only(data) {
        version_idx = match qr_version_index(data, &THRESHOLDS_BINARY) {
            Some(idx) => idx,
            _ => return Err(Error::OutOfRange),
        }
    } else if let Some(idx) = qr_version_index(data, &THRESHOLDS_ALPHANUM) {
        version_idx = idx;
        if data_len > THRESHOLDS_BINARY[idx] {
            for c in buffer.iter_mut() {
                c.make_ascii_uppercase()
            }
        };
    } else {
        return Err(Error::OutOfRange);
    }

    let size = QR_WIDTHS[version_idx];
    let scale = max_size / size;
    assert!((1..=10).contains(&scale));

    unsafe {
        buffer[data_len] = 0u8;
        let cstr = CStr::from_bytes_with_nul_unchecked(&buffer[..data_len + 1]);

        display_qrcode(x.into(), y.into(), cstr.as_ptr() as _, scale as u8);
        Ok(())
    }
}
