use super::{
    receiver_is_locked, receiver_lock, send_request, wait_for_response, BufferCounter, MsgType,
};
use crate::time::Duration;
use minicbor::Encoder;

const CHUNK_SIZE: usize = 256;
const MAX_PACKET_SIZE: usize = 512;

pub fn upload_image(image_data: &[u8], image_hash: &[u8]) -> bool {
    if receiver_is_locked() {
        return false;
    }

    let mut data = [0u8; MAX_PACKET_SIZE];
    let mut data_encoded = [0u8; MAX_PACKET_SIZE];

    let mut writer = BufferCounter::new(&mut data[8..]);

    let mut enc = Encoder::new(&mut writer);

    let mut rem_len = image_data.len();

    unwrap!(enc.map(5));
    unwrap!(enc.str("image"));
    unwrap!(enc.u8(0));
    unwrap!(enc.str("len"));
    unwrap!(enc.u64(rem_len as _));
    unwrap!(enc.str("off"));
    unwrap!(enc.u8(0));
    unwrap!(enc.str("hash"));
    unwrap!(enc.bytes(image_hash));
    unwrap!(enc.str("data"));
    unwrap!(enc.bytes(&image_data[..CHUNK_SIZE]));

    let encoded_len = writer.bytes_written();
    receiver_lock();

    send_request(&mut data, encoded_len, &mut data_encoded, 2, 1, 1);

    let mut resp_buffer = [0u8; 64];
    if wait_for_response(
        MsgType::ImageUploadResponse,
        &mut resp_buffer,
        Duration::from_millis(100),
    )
    .is_err()
    {
        return false;
    }

    rem_len = rem_len.saturating_sub(CHUNK_SIZE);

    let mut off: usize = CHUNK_SIZE;

    while rem_len > 0 {
        let mut data = [0u8; MAX_PACKET_SIZE];
        let mut data_encoded = [0u8; MAX_PACKET_SIZE];
        let mut writer = BufferCounter::new(&mut data[8..]);
        let mut enc = Encoder::new(&mut writer);

        let chunk_len = if rem_len > CHUNK_SIZE {
            CHUNK_SIZE
        } else {
            rem_len
        };

        unwrap!(enc.map(2));
        unwrap!(enc.str("off"));
        unwrap!(enc.u32(off as _));
        unwrap!(enc.str("data"));
        unwrap!(enc.bytes(&image_data[off..off + chunk_len]));

        let encoded_len = writer.bytes_written();

        receiver_lock();

        send_request(&mut data, encoded_len, &mut data_encoded, 2, 1, 1);

        let mut resp_buffer = [0u8; 64];
        if wait_for_response(
            MsgType::ImageUploadResponse,
            &mut resp_buffer,
            Duration::from_millis(100),
        )
        .is_err()
        {
            return false;
        }

        rem_len = rem_len.saturating_sub(chunk_len);
        off += chunk_len;
    }

    true
}
