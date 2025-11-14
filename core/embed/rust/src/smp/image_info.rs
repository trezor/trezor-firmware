use super::{
    receiver_acquire, receiver_release, send_request, wait_for_response, MsgType, SmpBuffer,
    SmpHeader, SMP_CMD_ID_IMAGE_STATE, SMP_GROUP_IMAGE, SMP_HEADER_SIZE, SMP_OP_READ,
};
use crate::time::Duration;
use minicbor::{data::Type, decode, Decoder, Encoder};

/// Get the version string of the active nRF app image (slot 0).
/// Writes directly into the provided buffer.
/// Returns the length of the version string (without null terminator), or 0 on
/// error.
pub fn get_version(buf: &mut [u8]) -> usize {
    let mut cbor_data = [0u8; 64];
    let mut data = [0u8; 64];
    let mut send_buffer = [0u8; 64];

    let mut writer = SmpBuffer::new(&mut cbor_data);
    let mut enc = Encoder::new(&mut writer);
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

    let res = send_request(&mut data[..SMP_HEADER_SIZE + data_len], &mut send_buffer);
    if res.is_err() {
        receiver_release();
        return 0;
    }

    let mut resp_buffer = [0u8; 256];
    if wait_for_response(
        MsgType::ImageStateResponse,
        &mut resp_buffer,
        Duration::from_millis(2000),
    )
    .is_ok()
    {
        // Parse and extract version directly from CBOR without allocating
        match extract_version_from_cbor(&resp_buffer, buf) {
            Ok(len) => {
                //receiver_release();
                len
            }
            Err(_) => {
                //receiver_release();
                0
            }
        }
    } else {
        //receiver_release();
        0
    }
}

/// Parse CBOR and extract version string directly into the provided buffer
fn extract_version_from_cbor(cbor: &[u8], out_buf: &mut [u8]) -> Result<usize, decode::Error> {
    let mut dec = Decoder::new(cbor);

    // Parse outer map
    match dec.map()? {
        Some(n) => {
            for _ in 0..n {
                let key = dec.str()?;
                if key == "images" {
                    return extract_version_from_images_array(&mut dec, out_buf);
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
                return extract_version_from_images_array(&mut dec, out_buf);
            } else {
                dec.skip()?;
            }
        },
    }

    Err(decode::Error::message("images array not found"))
}

fn extract_version_from_images_array(
    dec: &mut Decoder,
    out_buf: &mut [u8],
) -> Result<usize, decode::Error> {
    match dec.array()? {
        Some(n) => {
            if n > 0 {
                return extract_version_from_image_map(dec, out_buf);
            }
        }
        None => {
            loop {
                if let Type::Break = dec.datatype()? {
                    dec.skip()?;
                    break;
                }
                // Parse first image only
                return extract_version_from_image_map(dec, out_buf);
            }
        }
    }

    Err(decode::Error::message("no images found"))
}

fn extract_version_from_image_map(
    dec: &mut Decoder,
    out_buf: &mut [u8],
) -> Result<usize, decode::Error> {
    match dec.map()? {
        Some(n) => {
            for _ in 0..n {
                let key = dec.str()?;
                if key == "version" {
                    let version_str = dec.str()?;
                    let copy_len = core::cmp::min(version_str.len(), out_buf.len());
                    out_buf[..copy_len].copy_from_slice(&version_str.as_bytes()[..copy_len]);
                    return Ok(copy_len);
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
                let version_str = dec.str()?;
                let copy_len = core::cmp::min(version_str.len(), out_buf.len());
                out_buf[..copy_len].copy_from_slice(&version_str.as_bytes()[..copy_len]);
                return Ok(copy_len);
            } else {
                dec.skip()?;
            }
        },
    }

    Err(decode::Error::message("version key not found"))
}
