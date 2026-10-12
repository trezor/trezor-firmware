use minicbor::data::Type;
use minicbor::{Decoder, Encoder, decode};
use rtl::error::unwrap;
use sys::time::Duration;

use super::{
    MsgType, SMP_CMD_ID_IMAGE_UPLOAD, SMP_GROUP_IMAGE, SMP_HEADER_SIZE, SMP_OP_WRITE, SmpBuffer,
    SmpHeader, receiver_acquire, receiver_release, send_request, wait_for_response,
};

const CHUNK_SIZE: usize = 256;
const MAX_PACKET_SIZE: usize = 512;

pub fn upload_image(image_data: &[u8], image_hash: &[u8]) -> bool {
    let mut cbor_data = [0u8; MAX_PACKET_SIZE];
    let mut data = [0u8; MAX_PACKET_SIZE];
    let mut buffer = [0u8; MAX_PACKET_SIZE];

    let mut writer = SmpBuffer::new(&mut cbor_data);

    let mut enc = Encoder::new(&mut writer);

    unwrap!(enc.map(5));
    unwrap!(enc.str("image"));
    unwrap!(enc.u8(0));
    unwrap!(enc.str("len"));
    unwrap!(enc.u64(image_data.len() as _));
    unwrap!(enc.str("off"));
    unwrap!(enc.u8(0));
    unwrap!(enc.str("hash"));
    unwrap!(enc.bytes(image_hash));
    unwrap!(enc.str("data"));
    unwrap!(enc.bytes(&image_data[..CHUNK_SIZE]));

    let data_len = writer.bytes_written();
    unwrap!(receiver_acquire());

    let header = SmpHeader::new(
        SMP_OP_WRITE,
        data_len,
        SMP_GROUP_IMAGE,
        0,
        SMP_CMD_ID_IMAGE_UPLOAD,
    )
    .to_bytes();

    data[..SMP_HEADER_SIZE].copy_from_slice(&header);
    data[SMP_HEADER_SIZE..SMP_HEADER_SIZE + data_len].copy_from_slice(&cbor_data[..data_len]);

    let res = send_request(&mut data[..SMP_HEADER_SIZE + data_len], &mut buffer);

    if res.is_err() {
        receiver_release();
        return false;
    }

    if !wait_for_upload_ack(CHUNK_SIZE) {
        return false;
    }

    let mut offset = CHUNK_SIZE;

    for chunk in image_data.chunks(CHUNK_SIZE).skip(1) {
        let mut cbor_data = [0u8; MAX_PACKET_SIZE];
        let mut data = [0u8; MAX_PACKET_SIZE];
        let mut buffer = [0u8; MAX_PACKET_SIZE];
        let mut writer = SmpBuffer::new(&mut cbor_data);
        let mut enc = Encoder::new(&mut writer);

        unwrap!(enc.map(2));
        unwrap!(enc.str("off"));
        unwrap!(enc.u32(offset as _));
        unwrap!(enc.str("data"));
        unwrap!(enc.bytes(chunk));

        let data_len = writer.bytes_written();

        unwrap!(receiver_acquire());

        let header = SmpHeader::new(SMP_OP_WRITE, data_len, SMP_GROUP_IMAGE, 0, 1).to_bytes();

        data[..SMP_HEADER_SIZE].copy_from_slice(&header);
        data[SMP_HEADER_SIZE..SMP_HEADER_SIZE + data_len].copy_from_slice(&cbor_data[..data_len]);

        let res = send_request(&mut data[..SMP_HEADER_SIZE + data_len], &mut buffer);

        if res.is_err() {
            receiver_release();
            return false;
        }

        if !wait_for_upload_ack(offset + chunk.len()) {
            return false;
        }

        offset += CHUNK_SIZE;
    }

    true
}

/// Wait for the upload response and check that the device accepted the chunk,
/// i.e. reports `rc == 0` and expects the next chunk at `expected_off`.
/// MCUboot answers an out-of-sequence chunk with `rc == 0` and the offset it
/// actually expects, so the offset is what proves this chunk was written.
fn wait_for_upload_ack(expected_off: usize) -> bool {
    let mut resp_buffer = [0u8; 64];
    let Ok(len) = wait_for_response(
        MsgType::ImageUploadResponse,
        &mut resp_buffer,
        Duration::from_millis(500),
    ) else {
        return false;
    };

    matches!(
        parse_upload_response(&resp_buffer[..len]),
        Ok((0, Some(off))) if off as usize == expected_off
    )
}

// Walk CBOR: { "rc": <int>, "off": <uint>, ... }; a missing "rc" means success.
fn parse_upload_response(cbor: &[u8]) -> Result<(i32, Option<u32>), decode::Error> {
    let mut dec = Decoder::new(cbor);
    let mut rc = 0;
    let mut off = None;

    let mut remaining = dec.map()?;
    loop {
        match remaining {
            Some(0) => break,
            Some(ref mut n) => *n -= 1,
            None => {
                if let Type::Break = dec.datatype()? {
                    dec.skip()?;
                    break;
                }
            }
        }
        match dec.str()? {
            "rc" => rc = dec.i32()?,
            "off" => off = Some(dec.u32()?),
            _ => dec.skip()?,
        }
    }

    Ok((rc, off))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_upload_response() {
        // {"rc": 0, "off": 512}
        let ok = [
            0xa2, 0x62, b'r', b'c', 0x00, 0x63, b'o', b'f', b'f', 0x19, 0x02, 0x00,
        ];
        assert_eq!(parse_upload_response(&ok).unwrap(), (0, Some(512)));
        // {"rc": 3}
        let err = [0xa1, 0x62, b'r', b'c', 0x03];
        assert_eq!(parse_upload_response(&err).unwrap(), (3, None));
        // indefinite {"off": 256, "match": true}
        let indef = [
            0xbf, 0x63, b'o', b'f', b'f', 0x19, 0x01, 0x00, 0x65, b'm', b'a', b't', b'c', b'h',
            0xf5, 0xff,
        ];
        assert_eq!(parse_upload_response(&indef).unwrap(), (0, Some(256)));
        assert!(parse_upload_response(&[]).is_err());
    }
}
