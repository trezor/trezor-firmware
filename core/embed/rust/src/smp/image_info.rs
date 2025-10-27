use super::{
    receiver_acquire, receiver_release, send_request, wait_for_response, MsgType, SmpBuffer,
    SmpHeader, SMP_CMD_ID_ECHO, SMP_GROUP_OS, SMP_HEADER_SIZE, SMP_OP_READ,
};
use crate::time::Duration;
use minicbor::{data::Type, decode, Decoder, Encoder};

pub fn send(text: &str) -> bool {
    let mut cbor_data = [0u8; 64];
    let mut data = [0u8; 64];
    let mut buffer = [0u8; 64];

    let mut writer = SmpBuffer::new(&mut cbor_data);

    let mut enc = Encoder::new(&mut writer);
    unwrap!(enc.map(1));
    unwrap!(enc.str("d"));
    unwrap!(enc.str(text));

    unwrap!(receiver_acquire());

    let data_len = writer.bytes_written();

    let header = SmpHeader::new(SMP_OP_READ, data_len, SMP_GROUP_OS, 0, SMP_CMD_ID_ECHO).to_bytes();

    data[..SMP_HEADER_SIZE].copy_from_slice(&header);
    data[SMP_HEADER_SIZE..SMP_HEADER_SIZE + data_len].copy_from_slice(&cbor_data[..data_len]);

    let res = send_request(&mut data[..SMP_HEADER_SIZE + data_len], &mut buffer);

    if res.is_err() {
        receiver_release();
        return false;
    }

    let mut resp_buffer = [0u8; 64];
    if wait_for_response(MsgType::Echo, &mut resp_buffer, Duration::from_millis(100)).is_ok() {
        let echo_msg = process_msg(&resp_buffer);
        return if let Ok(msg) = echo_msg {
            msg == text
        } else {
            false
        };
    }

    false
}

fn process_msg(buf: &[u8]) -> Result<&str, decode::Error> {
    let mut dec = Decoder::new(buf);

    match dec.map()? {
        Some(n) => {
            // definite-length: iterate exactly n times
            for _ in 0..n {
                let key = dec.str()?;
                let val = dec.str()?;
                if key == "r" {
                    return Ok(val);
                }
            }
        }
        None => {
            // indefinite-length: keep reading until we hit the "break"
            loop {
                // peek at the next major type
                if let Type::Break = dec.datatype()? {
                    dec.skip()?; // consume the break
                    break;
                }
                let key = dec.str()?;
                let val = dec.str()?;
                if key == "r" {
                    return Ok(val);
                }
            }
        }
    }

    Err(decode::Error::message("key \"r\" not found"))
}
