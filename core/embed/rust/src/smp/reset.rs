use minicbor::Encoder;

use super::{
    send_request, SmpBuffer, SmpHeader, SMP_CMD_ID_RESET, SMP_GROUP_OS, SMP_HEADER_SIZE,
    SMP_OP_READ,
};

pub fn send() {
    let mut cbor_data = [0u8; 64];
    let mut data = [0u8; 64];
    let mut buffer = [0u8; 64];

    let mut writer = SmpBuffer::new(&mut cbor_data);

    let mut enc = Encoder::new(&mut writer);
    unwrap!(enc.map(0));

    let data_len = writer.bytes_written();

    let header =
        SmpHeader::new(SMP_OP_READ, data_len, SMP_GROUP_OS, 0, SMP_CMD_ID_RESET).to_bytes();

    data[..SMP_HEADER_SIZE].copy_from_slice(&header);
    data[SMP_HEADER_SIZE..SMP_HEADER_SIZE + data_len].copy_from_slice(&cbor_data[..data_len]);

    send_request(&mut data[..SMP_HEADER_SIZE + data_len], &mut buffer);
}
