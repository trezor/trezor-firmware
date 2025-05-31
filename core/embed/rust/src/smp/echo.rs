use super::{
    receiver_is_locked, receiver_lock, send_request, wait_for_response, BufferCounter, MsgType,
};
use crate::time::Duration;
use minicbor::{data::Type, decode, Decoder, Encoder};

pub fn send(text: &str) -> bool {
    if receiver_is_locked() {
        return false;
    }
    let mut data = [0u8; 64];
    let mut buffer = [0u8; 64];

    let mut writer = BufferCounter::new(&mut data[8..]);

    let mut enc = Encoder::new(&mut writer);
    unwrap!(enc.map(1));
    unwrap!(enc.str("d"));
    unwrap!(enc.str(text));

    receiver_lock();

    let encoded_len = writer.bytes_written();

    send_request(&mut data, encoded_len, &mut buffer, 0, 0, 0);

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

pub fn process_msg(buf: &[u8]) -> Result<&str, decode::Error> {
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
