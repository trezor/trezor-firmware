const PACKET_MARKER: u8 = b'?';
const HEADER_MAGIC: u8 = b'#';

pub type Packet = [u8; 64];
pub type Buffer = [u8; 8192];

pub enum CodecError {
    InvalidPacket,
    OutOfBounds,
}

pub struct Msg<'a> {
    pub id: u16,
    pub data: &'a [u8],
}

pub enum Decode<'a> {
    InProgress,
    Complete(Msg<'a>),
}

pub struct Decoder {
    state: State,
}

impl Decoder {
    pub fn new() -> Self {
        Self {
            state: State::Initial,
        }
    }

    pub fn decode_packet<'a>(
        &mut self,
        packet: &Packet,
        buffer: &'a mut Buffer,
    ) -> Result<Decode<'a>, CodecError> {
        match self.state {
            State::Initial => {
                let (id, len, data) = decode_init_packet(packet, buffer.len())?;

                buffer[..data.len()].copy_from_slice(data);

                if len > data.len() {
                    // More packets will follow. Transform into the `InProgress` state and expect
                    // more continuation packets.
                    self.state = State::InProgress {
                        id,
                        len,
                        buffered_len: data.len(),
                    };
                    Ok(Decode::InProgress)
                } else {
                    // This is the last packet. Transform into the `Initial` state and return the
                    // full message.
                    self.state = State::Initial;
                    Ok(Decode::Complete(Msg {
                        id,
                        data: &buffer[..len],
                    }))
                }
            }
            State::InProgress {
                id,
                len,
                buffered_len,
            } => {
                let remaining_len = len - buffered_len;
                let data = decode_cont_packet(packet, remaining_len)?;

                buffer[buffered_len..buffered_len + data.len()].copy_from_slice(data);

                if remaining_len > data.len() {
                    // More packets will follow. Shift the offset, stay in the `InProgress` state.
                    self.state = State::InProgress {
                        id,
                        len,
                        buffered_len: buffered_len + data.len(),
                    };
                    Ok(Decode::InProgress)
                } else {
                    // This is the last packet. Transform into the `Initial` state and return the
                    // full message.
                    self.state = State::Initial;
                    Ok(Decode::Complete(Msg {
                        id,
                        data: &buffer[..len],
                    }))
                }
            }
        }
    }
}

fn decode_init_packet(packet: &Packet, max_len: usize) -> Result<(u16, usize, &[u8]), CodecError> {
    if packet[0] != PACKET_MARKER || packet[1] != HEADER_MAGIC || packet[2] != HEADER_MAGIC {
        return Err(CodecError::InvalidPacket);
    }
    let id = u16::from_be_bytes([packet[3], packet[4]]);
    let len = u32::from_be_bytes([packet[5], packet[6], packet[7], packet[8]]) as usize;
    if len > max_len {
        return Err(CodecError::OutOfBounds);
    }
    let tail = &packet[9..]; // Skip the marker and header.
    let data = &tail[..tail.len().min(len)];
    Ok((id, len, data))
}

fn decode_cont_packet(packet: &Packet, max_len: usize) -> Result<&[u8], CodecError> {
    if packet[0] != PACKET_MARKER {
        return Err(CodecError::InvalidPacket);
    }
    let tail = &packet[1..]; // Skip the marker.
    let data = &tail[..tail.len().min(max_len)];
    Ok(data)
}

enum State {
    Initial,
    InProgress {
        id: u16,
        len: usize,
        buffered_len: usize,
    },
}

pub enum Encode {
    InProgress,
    Complete,
}

pub struct Encoder<'a> {
    msg: Msg<'a>,
    offset: usize,
}

impl<'a> Encoder<'a> {
    pub fn new(msg: Msg<'a>) -> Self {
        Self { msg, offset: 0 }
    }

    pub fn encode_packet(&mut self, packet: &mut Packet) -> Encode {
        packet[0] = PACKET_MARKER;
        let packet_offset = if self.offset == 0 {
            // Initial packet.
            packet[1] = HEADER_MAGIC;
            packet[2] = HEADER_MAGIC;
            packet[3..5].copy_from_slice(&self.msg.id.to_be_bytes());
            packet[5..9].copy_from_slice(&self.msg.data.len().to_be_bytes());
            9 // Skip marker and header.
        } else {
            // Continuation packet.
            1 // Skip just the marker.
        };

        // Compute how much data we can put into this packet.
        let data = &self.msg.data;
        let len_in_packet = packet.len() - packet_offset;
        let len_remaining = data.len() - self.offset;
        let len_to_copy = len_in_packet.min(len_remaining);

        packet[packet_offset..packet_offset + len_to_copy]
            .copy_from_slice(&data[self.offset..self.offset + len_to_copy]);
        self.offset += len_to_copy;
        if self.offset < data.len() {
            Encode::InProgress
        } else {
            Encode::Complete
        }
    }
}
