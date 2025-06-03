mod api;
mod base64;
mod crc16;
mod echo;
mod reset;
mod upload;

use crate::{
    time::{Duration, Instant},
    trezorhal::{
        irq::{irq_lock, irq_unlock},
        nrf::send_data,
    },
};
use base64::{base64_decode, base64_encode};
use core::{convert::Infallible, ptr};
use crc16::crc16_itu_t;
use minicbor::encode::write::Write;

const HEADER_SIZE: usize = 8;

// Frame sizing
const BOOT_SERIAL_FRAME_MTU_BIN: usize = 93;
const BOOT_SERIAL_FRAME_MTU: usize = 124;
const BOOT_SERIAL_MAX_MSG_SIZE: usize = 512;

// Frame start bytes
const START_INIT_FRAME_BYTE_0: u8 = 6;
const START_INIT_FRAME_BYTE_1: u8 = 9;
const START_CONT_FRAME_BYTE_0: u8 = 4;
const START_CONT_FRAME_BYTE_1: u8 = 20;

static mut SMP_RECEIVER: Option<SmpReceiver> = None;

#[derive(Debug)]
pub enum SmpError {
    Timeout,
    WrongMessage,
}

#[repr(C)]
struct SmpHeader {
    op: u8,
    _reserved: u8,
    len_hi: u8,
    len_lo: u8,
    group_id_hi: u8,
    group_id_lo: u8,
    seq: u8,
    cmd_id: u8,
}

impl SmpHeader {
    fn from_bytes(b: &[u8]) -> Self {
        // we assume b.len() >= HEADER_SIZE
        SmpHeader {
            op: b[0],
            _reserved: b[1],
            len_hi: b[2],
            len_lo: b[3],
            group_id_hi: b[4],
            group_id_lo: b[5],
            seq: b[6],
            cmd_id: b[7],
        }
    }
}

pub fn encode_request(data: &[u8], out: &mut [u8]) {
    let len = data.len();
    // same check as `if (max_out_len < (length + 3)) return;`
    if out.len() < len + 3 {
        return;
    }

    // length including CRC (2 bytes) and length field itself
    let length_field = (len + 2) as u16;
    out[0] = (length_field >> 8) as u8;
    out[1] = (length_field & 0xFF) as u8;

    // copy the payload
    out[2..2 + len].copy_from_slice(data);

    // compute CRC (assumes you have `crc16_itu_t(seed: u16, data: &[u8]) -> u16` in
    // scope)
    let crc = crc16_itu_t(0, data);

    // append CRC hi/lo
    out[len + 2] = (crc >> 8) as u8;
    out[len + 3] = (crc & 0xFF) as u8;
}

pub fn send_request(
    data: &mut [u8],
    data_len: usize,
    buffer: &mut [u8],
    op: u8,
    group: u16,
    cmd_id: u8,
) {
    create_header(data, op, data_len as u16, group, 0, cmd_id);

    encode_request(&data[..(data_len + 8)], buffer);

    let total = data_len + 8 + 2 + 2;

    let data = &buffer[..total];

    // One buffer big enough for header + max‐encoded data + newline
    //   header = 2 bytes
    //   base64 of BOOT_SERIAL_FRAME_MTU_BIN fits in BOOT_SERIAL_FRAME_MTU
    //   newline = 1 byte
    let mut buf = [0u8; 2 + BOOT_SERIAL_FRAME_MTU + 1];

    let mut init_frame = true;
    for chunk in data.chunks(BOOT_SERIAL_FRAME_MTU_BIN) {
        // 1) write the two‐byte header
        let (b0, b1) = if init_frame {
            (START_INIT_FRAME_BYTE_0, START_INIT_FRAME_BYTE_1)
        } else {
            (START_CONT_FRAME_BYTE_0, START_CONT_FRAME_BYTE_1)
        };
        buf[0] = b0;
        buf[1] = b1;

        let enc_len = unwrap!(base64_encode(chunk, &mut buf[2..]));

        // 3) append newline
        let total_len = 2 + enc_len;
        buf[total_len] = b'\n';

        // 4) send it out
        send_data(&buf[..total_len + 1]);

        init_frame = false;
    }
}

pub fn create_header(buffer: &mut [u8], op: u8, len: u16, group: u16, seq: u8, cmd_id: u8) {
    // If buffer is too small, do nothing (mirrors C behavior of no safety check)
    if buffer.len() < 8 {
        return;
    }

    let len_be = len.to_be_bytes(); // [hi, lo]
    let group_be = group.to_be_bytes(); // [hi, lo]

    buffer[0] = op;
    buffer[1] = 0;
    buffer[2] = len_be[0];
    buffer[3] = len_be[1];
    buffer[4] = group_be[0];
    buffer[5] = group_be[1];
    buffer[6] = seq;
    buffer[7] = cmd_id;
}

/// A simple writer that copies into a `&mut [u8]` and counts bytes written.
pub struct BufferCounter<'a> {
    buf: &'a mut [u8],
    written: usize,
}

impl<'a> BufferCounter<'a> {
    /// Wrap your buffer:
    pub fn new(buf: &'a mut [u8]) -> Self {
        BufferCounter { buf, written: 0 }
    }

    /// How many bytes have been written so far?
    pub fn bytes_written(&self) -> usize {
        self.written
    }

    /// Get the filled portion of the buffer.
    pub fn filled(&self) -> &[u8] {
        &self.buf[..self.written]
    }
}

impl<'a> Write for BufferCounter<'a> {
    type Error = Infallible;

    fn write_all(&mut self, data: &[u8]) -> Result<(), Self::Error> {
        let end = self.written + data.len();
        // In production you might guard against overflow:
        // if end > self.buf.len() { return Err(...); }
        self.buf[self.written..end].copy_from_slice(data);
        self.written = end;
        Ok(())
    }
}

#[derive(Copy, Clone, PartialEq)]
pub enum MsgType {
    Echo,
    ImageUploadResponse,
    Unknown,
}

#[derive(Copy, Clone)]
pub struct SmpReceiver {
    rx_frame: [u8; BOOT_SERIAL_FRAME_MTU + 3],
    rx_frame_len: usize,
    rx_frame_dec: [u8; BOOT_SERIAL_FRAME_MTU + 3],
    rx_msg: [u8; BOOT_SERIAL_MAX_MSG_SIZE + 1],
    rx_msg_len: usize,
    msg_type: Option<MsgType>,
}

impl SmpReceiver {
    pub fn new() -> Self {
        Self {
            rx_frame: [0; BOOT_SERIAL_FRAME_MTU + 3],
            rx_frame_len: 0,
            rx_frame_dec: [0; BOOT_SERIAL_FRAME_MTU + 3],
            rx_msg: [0; BOOT_SERIAL_MAX_MSG_SIZE + 1],
            rx_msg_len: 0,
            msg_type: None,
        }
    }

    /// Call this for each incoming byte
    pub fn process_byte(&mut self, byte: u8) {
        if self.msg_type.is_some() {
            return;
        }

        if byte == b'\n' {
            // end of a frame
            if self.rx_frame_len > 0 {
                let frame = &self.rx_frame[..self.rx_frame_len];

                // init or continuation?
                if frame[0] == START_INIT_FRAME_BYTE_0 && frame[1] == START_INIT_FRAME_BYTE_1 {
                    self.rx_msg_len = 0;
                    self.process_frame();
                } else if frame[0] == START_CONT_FRAME_BYTE_0
                    && frame[1] == START_CONT_FRAME_BYTE_1
                    && self.rx_msg_len != 0
                {
                    self.process_frame();
                }
            }
            // reset for next frame
            self.rx_frame_len = 0;
        } else {
            // accumulate into smp_rx_frame[]
            if self.rx_frame_len < self.rx_frame.len() {
                self.rx_frame[self.rx_frame_len] = byte;
                self.rx_frame_len += 1;
            }
        }
    }

    /// Handle one decoded frame chunk
    fn process_frame(&mut self) {
        // Base64‐decode into smp_rx_frame_dec[]
        let decode_res =
            base64_decode(&self.rx_frame[2..self.rx_frame_len], &mut self.rx_frame_dec);

        if let Ok(len) = decode_res {
            if len > 0 {
                // copy into last_msg at current offset
                let remaining = self.rx_msg.len().saturating_sub(self.rx_msg_len);
                let copy_len = len.min(remaining);

                self.rx_msg[self.rx_msg_len..self.rx_msg_len + copy_len]
                    .copy_from_slice(&self.rx_frame_dec[..copy_len]);

                let received_len = self.rx_msg_len + len;

                // the first two bytes of last_msg are the length field
                let msg_len = ((self.rx_msg[0] as u16) << 8) | (self.rx_msg[1] as u16);

                // too long?
                if received_len.saturating_sub(2) > msg_len as usize {
                    self.rx_msg_len = 0;
                    return;
                }

                // advance offset by the *full* decoded length
                self.rx_msg_len = received_len;

                // complete?
                if received_len.saturating_sub(2) == msg_len as usize {
                    // TODO: CRC check here

                    self.process_msg(msg_len as _);
                }
            }
        }
    }

    fn process_msg(self: &mut SmpReceiver, msg_len: usize) {
        // hand off [2..2+msg_len] as header+payload
        let start = 2;
        let end = start + msg_len;

        let msg = &self.rx_msg[start..end];

        // too short?
        if msg.len() < HEADER_SIZE {
            return;
        }

        let hdr = SmpHeader::from_bytes(&msg[..HEADER_SIZE]);
        let group = ((hdr.group_id_hi as u16) << 8) | (hdr.group_id_lo as u16);
        let cmd_id = hdr.cmd_id;

        match (group, cmd_id) {
            (0, 0) => {
                self.msg_type = Some(MsgType::Echo);
            }
            (1, 1) => {
                self.msg_type = Some(MsgType::ImageUploadResponse);
            }
            _ => self.msg_type = Some(MsgType::Unknown),
        }
    }
}

pub fn process_rx_byte(byte: u8) {
    let opt = unsafe { ptr::read_volatile(&raw mut SMP_RECEIVER) };
    if let Some(mut receiver) = opt {
        receiver.process_byte(byte);
        unsafe {
            ptr::write_volatile(&raw mut SMP_RECEIVER, Some(receiver));
        }
    }
}

pub fn receiver_is_locked() -> bool {
    let key = irq_lock();
    let result = unsafe { ptr::read_volatile(&raw mut SMP_RECEIVER).is_some() };
    irq_unlock(key);
    result
}

pub fn receiver_unlock() {
    let key = irq_lock();
    unsafe {
        ptr::write_volatile(&raw mut SMP_RECEIVER, None);
    }
    irq_unlock(key);
}

pub fn receiver_lock() {
    let key = irq_lock();
    let new_rcv = SmpReceiver::new();
    unsafe {
        ptr::write_volatile(&raw mut SMP_RECEIVER, Some(new_rcv));
    }
    irq_unlock(key);
}

pub fn receiver_read() -> SmpReceiver {
    let key = irq_lock();
    let opt = unsafe { ptr::read_volatile(&raw mut SMP_RECEIVER) };
    irq_unlock(key);
    if let Some(receiver) = opt {
        receiver
    } else {
        fatal_error!("Receiver is not initialized");
    }
}

pub fn wait_for_response(
    expected_msg_type: MsgType,
    buf: &mut [u8],
    timeout: Duration,
) -> Result<usize, SmpError> {
    let start = Instant::now();
    loop {
        let receiver = receiver_read();
        if let Some(msg_type) = receiver.msg_type {
            if msg_type != expected_msg_type {
                return Err(SmpError::WrongMessage);
            }

            let data = &receiver.rx_msg[10..receiver.rx_msg_len - 2];
            let data_len = data.len();

            let len = if data_len <= buf.len() {
                // copy only as many bytes as we have in `data`
                buf[..data_len].copy_from_slice(data);
                // return how many bytes we copied
                data_len
            } else {
                fatal_error!("Buffer too small");
            };

            receiver_unlock();

            return Ok(len);
        }

        if Instant::now().checked_duration_since(start) > Some(timeout) {
            // timeout reached
            receiver_unlock();
            return Err(SmpError::Timeout);
        }
    }
}
