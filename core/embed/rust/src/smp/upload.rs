use super::{
    receiver_acquire, send_request, wait_for_response, MsgType, SmpBuffer, SmpHeader,
    SMP_CMD_ID_IMAGE_UPLOAD, SMP_GROUP_IMAGE, SMP_HEADER_SIZE, SMP_OP_WRITE,
};
use crate::time::Duration;
use minicbor::Encoder;

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

    send_request(&mut data[..SMP_HEADER_SIZE + data_len], &mut buffer);

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

        send_request(&mut data[..SMP_HEADER_SIZE + data_len], &mut buffer);

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

        offset += CHUNK_SIZE;
    }

    true
}
