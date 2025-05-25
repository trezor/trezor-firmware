use minicbor::Encoder;

use super::{send_request, BufferCounter};

pub fn send() {
    let mut data = [0u8; 64];
    let mut buffer = [0u8; 64];

    let mut writer = BufferCounter::new(&mut data[8..]);

    let mut enc = Encoder::new(&mut writer);
    unwrap!(enc.map(0));

    let encoded_len = writer.bytes_written();

    send_request(&mut data, encoded_len, &mut buffer, 0, 0, 5);
}
