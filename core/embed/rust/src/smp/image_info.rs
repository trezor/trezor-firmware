use super::{
    receiver_acquire, receiver_release, send_request, wait_for_response, MsgType, SmpBuffer,
    SmpHeader, SMP_CMD_ID_IMAGE_STATE, SMP_GROUP_IMAGE, SMP_HEADER_SIZE, SMP_OP_READ,
};
use crate::time::Duration;
use minicbor::{data::Type, decode, Decoder, Encoder};

/// MCUboot-compatible version structure matching image header format
#[derive(Clone, Copy, Debug)]
pub struct AppVersion {
    pub major: u8,
    pub minor: u8,
    pub revision: u16,
    pub build_num: u32,
}

/// Parse "<major>.<minor>.<revision>[.<build>]" into AppVersion (no allocation)
/// Matches MCUboot image header version format
/// Examples: "1.0.3", "1.0.3.0", "255.255.65535.4294967295"
fn parse_app_version(s: &str) -> Option<AppVersion> {
    let mut parts = s.split('.');

    let major = parts.next()?.parse::<u8>().ok()?;
    let minor = parts.next()?.parse::<u8>().ok()?;
    let revision = parts.next()?.parse::<u16>().ok()?;

    // Build number is optional (defaults to 0 if absent)
    let build_num = parts
        .next()
        .filter(|b| !b.is_empty())
        .map_or(Some(0), |b| b.parse::<u32>().ok())?;

    // Reject if there are more than 4 parts
    if parts.next().is_some() {
        return None;
    }

    Some(AppVersion {
        major,
        minor,
        revision,
        build_num,
    })
}

/// Send SMP Image State request, parse CBOR, and return parsed version numbers.
pub fn get_version_numbers() -> Option<AppVersion> {
    let mut cbor_data = [0u8; 16];
    let mut data = [0u8; 32];
    let mut tx_buf = [0u8; 64];

    let mut writer = SmpBuffer::new(&mut cbor_data);
    let mut enc = Encoder::new(&mut writer);
    // Empty map as request body
    unwrap!(enc.map(0));

    unwrap!(receiver_acquire());

    let data_len = writer.bytes_written();
    let header = SmpHeader::new(
        SMP_OP_READ,
        data_len,
        SMP_GROUP_IMAGE,
        0,
        SMP_CMD_ID_IMAGE_STATE,
    )
    .to_bytes();

    data[..SMP_HEADER_SIZE].copy_from_slice(&header);
    data[SMP_HEADER_SIZE..SMP_HEADER_SIZE + data_len].copy_from_slice(&cbor_data[..data_len]);

    if send_request(&mut data[..SMP_HEADER_SIZE + data_len], &mut tx_buf).is_err() {
        receiver_release();
        return None;
    }

    let mut cbor_payload = [0u8; 256];
    let res = wait_for_response(
        MsgType::ImageStateResponse,
        &mut cbor_payload,
        Duration::from_millis(2000),
    );
    if res.is_err() {
        return None;
    }

    extract_version_numbers_from_cbor(&cbor_payload).ok()
}

// Walk CBOR: { "images": [ { "version": "x.y.z[.t]" , ... } , ... ], ... }
fn extract_version_numbers_from_cbor(cbor: &[u8]) -> Result<AppVersion, decode::Error> {
    let mut dec = Decoder::new(cbor);

    // Outer map (definite/indefinite)
    match dec.map()? {
        Some(n) => {
            for _ in 0..n {
                let key = dec.str()?;
                if key == "images" {
                    return parse_images_array_for_version(&mut dec);
                } else {
                    dec.skip()?;
                }
            }
        }
        None => loop {
            if let Type::Break = dec.datatype()? {
                dec.skip()?;
                break;
            }
            let key = dec.str()?;
            if key == "images" {
                return parse_images_array_for_version(&mut dec);
            } else {
                dec.skip()?;
            }
        },
    }

    Err(decode::Error::message("images not found"))
}

fn parse_images_array_for_version(dec: &mut Decoder) -> Result<AppVersion, decode::Error> {
    match dec.array()? {
        Some(n) => {
            // Read first element only
            if n == 0 {
                return Err(decode::Error::message("no images"));
            }
            parse_image_map_for_version(dec)
        }
        None => {
            // Indefinite array: read first item, then stop
            if let Type::Break = dec.datatype()? {
                dec.skip()?;
                return Err(decode::Error::message("no images"));
            }
            parse_image_map_for_version(dec)
        }
    }
}

fn parse_image_map_for_version(dec: &mut Decoder) -> Result<AppVersion, decode::Error> {
    match dec.map()? {
        Some(n) => {
            for _ in 0..n {
                let key = dec.str()?;
                if key == "version" {
                    let s = dec.str()?;
                    return parse_app_version(s)
                        .ok_or_else(|| decode::Error::message("bad version string"));
                } else {
                    dec.skip()?;
                }
            }
        }
        None => loop {
            if let Type::Break = dec.datatype()? {
                dec.skip()?;
                break;
            }
            let key = dec.str()?;
            if key == "version" {
                let s = dec.str()?;
                return parse_app_version(s)
                    .ok_or_else(|| decode::Error::message("bad version string"));
            } else {
                dec.skip()?;
            }
        },
    }
    Err(decode::Error::message("version not found"))
}
