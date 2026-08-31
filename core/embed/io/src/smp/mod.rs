mod api;
mod base64;
mod crc16;
mod echo;
mod image_info;
mod reset;
mod upload;

use core::cell::UnsafeCell;
use core::convert::Infallible;

use base64::{base64_decode, base64_encode};
use crc16::crc16_itu_t;
use minicbor::encode::write::Write;
use rtl::error::unwrap;
use sys::irq::{irq_lock, irq_unlock};
use sys::time::{Duration, Instant};

use crate::nrf::send_data;

pub const SMP_HEADER_SIZE: usize = 8;

pub const SMP_GROUP_OS: u16 = 0;
pub const SMP_GROUP_IMAGE: u16 = 1;

pub const SMP_CMD_ID_ECHO: u8 = 0;
pub const SMP_CMD_ID_RESET: u8 = 5;
pub const SMP_CMD_ID_IMAGE_STATE: u8 = 0;
pub const SMP_CMD_ID_IMAGE_UPLOAD: u8 = 1;

pub const SMP_OP_READ: u8 = 0;
pub const SMP_OP_READ_RSP: u8 = 1;
pub const SMP_OP_WRITE: u8 = 2;
pub const SMP_OP_WRITE_RSP: u8 = 3;

const MSG_HEADER_SIZE: usize = 2;
const MSG_FOOTER_SIZE: usize = 2;

const FRAME_HEADER_SIZE: usize = 2;
const FRAME_FOOTER_SIZE: usize = 1; // newline

// Frame sizing
const BOOT_SERIAL_FRAME_MTU_BIN: usize = 93;
const BOOT_SERIAL_FRAME_MTU: usize = 124;
const BOOT_SERIAL_MAX_MSG_SIZE: usize = 512;

// Frame start bytes
const START_INIT_FRAME_BYTE_0: u8 = 6;
const START_INIT_FRAME_BYTE_1: u8 = 9;
const START_CONT_FRAME_BYTE_0: u8 = 4;
const START_CONT_FRAME_BYTE_1: u8 = 20;

/// ReceiverStorage wraps an UnsafeCell<Option<SmpReceiver>> in a static.
/// SAFETY: We need manual synchronization (irq_lock/irq_unlock) whenever
/// accessing this static. UnsafeCell allows interior mutability, but we must
/// ensure only one context writes at a time.
struct ReceiverStorage(UnsafeCell<Option<SmpReceiver>>);
static SMP_RECEIVER: ReceiverStorage = ReceiverStorage(UnsafeCell::new(None));

/// We assert that it is safe to share `ReceiverStorage` across
/// threads/interrupt contexts because we manually lock interrupts
/// (irq_lock/irq_unlock) around all accesses. SAFETY: If any code touches
/// SMP_RECEIVER without locking IRQ, data races could occur.
unsafe impl Sync for ReceiverStorage {}

#[cfg_attr(test, derive(Debug))]
pub enum SmpError {
    Timeout,
    WrongMessage,
    Busy,
}

pub struct SmpHeader {
    op: u8,
    _reserved: u8,
    len: usize,
    group: u16,
    seq: u8,
    cmd_id: u8,
}

impl SmpHeader {
    pub fn new(op: u8, len: usize, group: u16, seq: u8, cmd_id: u8) -> Self {
        SmpHeader {
            op,
            _reserved: 0,
            len,
            group,
            seq,
            cmd_id,
        }
    }

    pub fn from_bytes(b: &[u8]) -> Self {
        // we assume b.len() >= HEADER_SIZE

        let len: u16 = u16::from_be_bytes([b[2], b[3]]);
        let group: u16 = u16::from_be_bytes([b[4], b[5]]); // [hi, lo]

        SmpHeader {
            op: b[0],
            _reserved: b[1],
            len: len as usize,
            group,
            seq: b[6],
            cmd_id: b[7],
        }
    }

    pub fn to_bytes(&self) -> [u8; SMP_HEADER_SIZE] {
        let len_be = (self.len as u16).to_be_bytes(); // [hi, lo]
        let group_be = self.group.to_be_bytes(); // [hi, lo]
        [
            self.op,
            self._reserved,
            len_be[0],
            len_be[1],
            group_be[0],
            group_be[1],
            self.seq,
            self.cmd_id,
        ]
    }
}

pub fn encode_request(data: &[u8], out: &mut [u8]) {
    let len = data.len();

    if out.len() < len + MSG_HEADER_SIZE + MSG_FOOTER_SIZE {
        return;
    }

    // length including CRC (2 bytes) and length field itself
    let length_field = (len + MSG_HEADER_SIZE) as u16;
    out[0] = (length_field >> 8) as u8;
    out[1] = (length_field & 0xFF) as u8;

    // copy the payload
    out[MSG_HEADER_SIZE..MSG_HEADER_SIZE + len].copy_from_slice(data);

    // compute CRC
    let crc = crc16_itu_t(0, data);

    // append CRC hi/lo
    out[len + MSG_HEADER_SIZE] = (crc >> 8) as u8;
    out[len + MSG_HEADER_SIZE + 1] = (crc & 0xFF) as u8;
}

pub fn send_request(data: &mut [u8], buffer: &mut [u8]) -> Result<(), SmpError> {
    encode_request(data, buffer);

    let total = data.len() + MSG_HEADER_SIZE + MSG_FOOTER_SIZE;

    let data = &buffer[..total];

    // One buffer big enough for header + max‐encoded data + newline
    //   header = 2 bytes
    //   base64 of BOOT_SERIAL_FRAME_MTU_BIN fits in BOOT_SERIAL_FRAME_MTU
    //   newline = 1 byte
    let mut buf = [0u8; FRAME_HEADER_SIZE + BOOT_SERIAL_FRAME_MTU + FRAME_FOOTER_SIZE];

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

        let enc_len = unwrap!(base64_encode(chunk, &mut buf[FRAME_HEADER_SIZE..]));

        // 3) append newline
        let total_len = FRAME_HEADER_SIZE + enc_len;
        buf[total_len] = b'\n';

        // 4) send it out
        let sent = send_data(&buf[..total_len + FRAME_FOOTER_SIZE], 10);

        if !sent {
            return Err(SmpError::Timeout);
        }

        init_frame = false;
    }

    Ok(())
}

/// A simple writer that copies into a `&mut [u8]` and counts bytes written.
pub struct SmpBuffer<'a> {
    buf: &'a mut [u8],
    written: usize,
}

impl<'a> SmpBuffer<'a> {
    /// Wrap your buffer:
    pub fn new(buf: &'a mut [u8]) -> Self {
        SmpBuffer { buf, written: 0 }
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

impl<'a> Write for SmpBuffer<'a> {
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
    ImageStateResponse,
    ImageUploadResponse,
    Unknown,
}

#[derive(Copy, Clone)]
pub struct SmpReceiver {
    rx_frame: [u8; BOOT_SERIAL_FRAME_MTU + FRAME_HEADER_SIZE + FRAME_FOOTER_SIZE],
    rx_frame_len: usize,
    rx_frame_dec: [u8; BOOT_SERIAL_FRAME_MTU + FRAME_HEADER_SIZE + FRAME_FOOTER_SIZE],
    rx_msg: [u8; BOOT_SERIAL_MAX_MSG_SIZE],
    rx_msg_len: usize,
    msg_type: Option<MsgType>,
}

impl SmpReceiver {
    pub fn new() -> Self {
        Self {
            rx_frame: [0; BOOT_SERIAL_FRAME_MTU + FRAME_HEADER_SIZE + FRAME_FOOTER_SIZE],
            rx_frame_len: 0,
            rx_frame_dec: [0; BOOT_SERIAL_FRAME_MTU + FRAME_HEADER_SIZE + FRAME_FOOTER_SIZE],
            rx_msg: [0; BOOT_SERIAL_MAX_MSG_SIZE],
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
            if self.rx_frame_len >= FRAME_HEADER_SIZE {
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
        // Base64‐decode into rx_frame_dec[]
        let decode_res =
            base64_decode(&self.rx_frame[2..self.rx_frame_len], &mut self.rx_frame_dec);

        if let Ok(len) = decode_res {
            if len > 0 {
                // copy into rx_msg at current offset
                let remaining = self.rx_msg.len().saturating_sub(self.rx_msg_len);
                let copy_len = len.min(remaining);

                self.rx_msg[self.rx_msg_len..self.rx_msg_len + copy_len]
                    .copy_from_slice(&self.rx_frame_dec[..copy_len]);

                let received_len = self.rx_msg_len + len;

                if received_len < MSG_HEADER_SIZE {
                    self.rx_msg_len = 0;
                    return;
                }

                // the first two bytes of rx_msg are the length field
                let msg_len = usize::from(u16::from_be_bytes([self.rx_msg[0], self.rx_msg[1]]));

                // The length field is attacker-controlled and `rx_msg` is a
                // fixed buffer, so a message that claims more than we can hold
                // is dropped rather than tracked. Without this the offset below
                // walks past the end of `rx_msg`, because it advances by the
                // full decoded length while the copy above is clamped.
                if msg_len + MSG_HEADER_SIZE > self.rx_msg.len() {
                    self.rx_msg_len = 0;
                    return;
                }

                // too long? (received_len - 2) > msg_len
                if received_len.saturating_sub(MSG_HEADER_SIZE) > msg_len {
                    self.rx_msg_len = 0;
                    return;
                }

                // advance offset by the *full* decoded length
                self.rx_msg_len = received_len;

                // complete?
                if received_len.saturating_sub(MSG_HEADER_SIZE) == msg_len {
                    // TODO: CRC check here

                    self.process_msg(msg_len);
                }
            }
        }
    }

    fn process_msg(self: &mut SmpReceiver, msg_len: usize) {
        // hand off [2..2+msg_len] as header+payload
        let start = MSG_HEADER_SIZE;
        let end = start + msg_len;

        let msg = &self.rx_msg[start..end];

        // too short?
        if msg.len() < SMP_HEADER_SIZE {
            return;
        }

        let hdr = SmpHeader::from_bytes(&msg[..SMP_HEADER_SIZE]);
        let group = hdr.group;
        let cmd_id = hdr.cmd_id;

        match (group, cmd_id) {
            (SMP_GROUP_OS, SMP_CMD_ID_ECHO) => {
                self.msg_type = Some(MsgType::Echo);
            }
            (SMP_GROUP_IMAGE, SMP_CMD_ID_IMAGE_STATE) => {
                self.msg_type = Some(MsgType::ImageStateResponse);
            }
            (SMP_GROUP_IMAGE, SMP_CMD_ID_IMAGE_UPLOAD) => {
                self.msg_type = Some(MsgType::ImageUploadResponse);
            }
            _ => self.msg_type = Some(MsgType::Unknown),
        }
    }
}

/// Called from interrupt context.
pub fn process_rx_byte(byte: u8) {
    // SAFETY: Called from interrupt context so no concurrency
    unsafe {
        let opt_ref: &mut Option<SmpReceiver> = &mut *SMP_RECEIVER.0.get();
        if let Some(receiver) = opt_ref.as_mut() {
            receiver.process_byte(byte);
        }
    }
}

pub fn receiver_release() {
    let key = irq_lock();

    // SAFETY: Protected by IRQ lock. Resets Option<SmpReceiver> → None
    unsafe {
        let opt_ref: &mut Option<SmpReceiver> = &mut *SMP_RECEIVER.0.get();
        *opt_ref = None;
    }

    irq_unlock(key);
}

pub fn receiver_acquire() -> Result<(), SmpError> {
    let key = irq_lock();

    // SAFETY: Protected by IRQ lock
    let already_acquired = unsafe {
        let opt_ref: &Option<SmpReceiver> = &*SMP_RECEIVER.0.get();
        opt_ref.is_some()
    };

    if already_acquired {
        irq_unlock(key);
        return Err(SmpError::Busy);
    }

    let new_rcv = SmpReceiver::new();
    // SAFETY: Protected by IRQ lock
    unsafe {
        let opt_mut: &mut Option<SmpReceiver> = &mut *SMP_RECEIVER.0.get();
        *opt_mut = Some(new_rcv);
    }

    irq_unlock(key);
    Ok(())
}

/// Read message type without removing it.
/// SAFETY: Unsafe because we access static mutable without compile-time borrow
/// checks. Must always be called with IRQ lock held.
unsafe fn receiver_read_msg_type() -> Option<MsgType> {
    // SAFETY: Caller must hold lock to avoid races.
    let msg_type = unsafe {
        let opt_ref: &Option<SmpReceiver> = &*SMP_RECEIVER.0.get();
        unwrap!(opt_ref.as_ref().map(|r| r.msg_type))
    };

    msg_type
}

/// Copy received message payload (excluding header/footer) into `buf`.
/// Returns the payload length on success.
/// SAFETY: Caller must hold IRQ lock, and `buf` must be large enough.
/// Also, `unwrap!` will panic if `opt_ref` is None (i.e., no receiver
/// acquired).
unsafe fn received_read_msg(buf: &mut [u8]) -> Result<usize, SmpError> {
    // SAFETY: Caller held lock, so safe to read.
    let receiver_ref = unsafe {
        let opt_ref: &Option<SmpReceiver> = &*SMP_RECEIVER.0.get();
        unwrap!(opt_ref.as_ref(), "Receiver is not initialized")
    };

    let data_start = MSG_HEADER_SIZE + SMP_HEADER_SIZE;

    // A response can claim a length that leaves no room for the payload the
    // layout below assumes - `process_msg()` only requires the SMP header, and
    // the footer is subtracted here. Reject instead of slicing an inverted or
    // underflowing range.
    if receiver_ref.rx_msg_len < data_start + MSG_FOOTER_SIZE {
        return Err(SmpError::WrongMessage);
    }

    let data_end = receiver_ref.rx_msg_len - MSG_FOOTER_SIZE;
    let data = &receiver_ref.rx_msg[data_start..data_end];
    let data_len = data.len();

    // The response length is chosen by the peer, so a payload that does not
    // fit the caller's buffer is its problem to report, not a reason to abort.
    if data_len > buf.len() {
        return Err(SmpError::WrongMessage);
    }

    buf[..data_len].copy_from_slice(data);

    Ok(data_len)
}

pub fn wait_for_response(
    expected_msg_type: MsgType,
    buf: &mut [u8],
    timeout: Duration,
) -> Result<usize, SmpError> {
    let start = Instant::now();
    loop {
        let key = irq_lock();
        // SAFETY: IRQ locked
        let msg_type = unsafe { receiver_read_msg_type() };
        irq_unlock(key);
        if let Some(msg_type) = msg_type {
            if msg_type != expected_msg_type {
                receiver_release();
                return Err(SmpError::WrongMessage);
            }

            let key = irq_lock();
            // SAFETY: IRQ locked, safe to read and clear receiver
            let result = unsafe { received_read_msg(buf) };
            irq_unlock(key);

            receiver_release();

            // a malformed response is the peer's problem, not ours: report it
            // rather than unwrapping into a panic
            return result;
        }

        if Instant::now().checked_duration_since(start) > Some(timeout) {
            // timeout reached
            receiver_release();
            return Err(SmpError::Timeout);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Feed one wire frame: [hdr0, hdr1] + base64(chunk) + '\n'
    fn feed_frame(r: &mut SmpReceiver, chunk: &[u8], init: bool) {
        let mut enc = [0u8; 256];
        let n = base64_encode(chunk, &mut enc).unwrap();
        if init {
            r.process_byte(START_INIT_FRAME_BYTE_0);
            r.process_byte(START_INIT_FRAME_BYTE_1);
        } else {
            r.process_byte(START_CONT_FRAME_BYTE_0);
            r.process_byte(START_CONT_FRAME_BYTE_1);
        }
        for b in &enc[..n] {
            r.process_byte(*b);
        }
        r.process_byte(b'\n');
    }

    /// A message body: two-byte length field followed by `payload`.
    fn body(claimed_len: u16, payload: &[u8]) -> Vec<u8> {
        let mut v = Vec::new();
        v.extend_from_slice(&claimed_len.to_be_bytes());
        v.extend_from_slice(payload);
        v
    }

    /// A frame shorter than the two-byte frame header must not be inspected
    /// as though it had one.
    #[test]
    fn short_frame_is_dropped() {
        let mut r = SmpReceiver::new();
        r.process_byte(START_INIT_FRAME_BYTE_0);
        r.process_byte(b'\n');
        assert!(r.msg_type.is_none());
        assert_eq!(r.rx_msg_len, 0);
    }

    /// An init frame carrying only one byte leaves the length field half
    /// written; it must be dropped rather than parsed against a stale byte.
    #[test]
    fn init_frame_without_full_length_field_is_dropped() {
        let mut r = SmpReceiver::new();
        // leave a stale low byte behind from a dropped message
        feed_frame(&mut r, &body(0xFF10, &[0xAA; 91]), true);
        assert_eq!(r.rx_msg[1], 0x10);

        // one byte alone would have claimed 0x0110 with that stale byte
        feed_frame(&mut r, &[0x01], true);
        assert_eq!(r.rx_msg_len, 0);
        assert!(r.msg_type.is_none());

        // a continuation must not resurrect it
        feed_frame(&mut r, &[0xBB; 16], false);
        assert_eq!(r.rx_msg_len, 0);
        assert!(r.msg_type.is_none());
    }

    /// The offset advances by the full decoded length while the copy is
    /// clamped, so a message claiming more than `rx_msg` holds must be
    /// dropped up front.
    #[test]
    fn message_longer_than_buffer_is_dropped() {
        let mut r = SmpReceiver::new();
        feed_frame(&mut r, &body(0xFFFF, &[0xAA; 91]), true);
        for _ in 0..8 {
            feed_frame(&mut r, &[0xBB; 93], false);
        }
        assert!(r.msg_type.is_none());
        assert_eq!(r.rx_msg_len, 0);
    }

    /// Same, for a claimed length that would complete exactly one frame past
    /// the end of the buffer.
    #[test]
    fn message_completing_past_buffer_is_dropped() {
        let mut r = SmpReceiver::new();
        feed_frame(&mut r, &body(600, &[0xAA; 91]), true);
        for _ in 0..4 {
            feed_frame(&mut r, &[0xBB; 93], false);
        }
        feed_frame(&mut r, &[0xBB; 44], false);
        feed_frame(&mut r, &[0xBB; 93], false);
        assert!(r.msg_type.is_none());
    }

    /// A response whose length field leaves no room for the payload the
    /// layout assumes must be reported, not sliced.
    #[test]
    fn response_without_payload_room_is_rejected() {
        let mut r = SmpReceiver::new();
        let hdr = [SMP_OP_READ_RSP, 0, 0, 0, 0, 0, 0, 0]; // group 0, cmd 0 = echo
        feed_frame(&mut r, &body(8, &hdr), true);

        // the parser accepts it as complete, so the guard has to be downstream
        assert!(r.msg_type.is_some());
        assert_eq!(r.rx_msg_len, 10);

        let data_start = MSG_HEADER_SIZE + SMP_HEADER_SIZE;
        assert!(r.rx_msg_len < data_start + MSG_FOOTER_SIZE);
    }

    /// A well-formed echo response is still accepted and located correctly.
    #[test]
    fn well_formed_response_is_accepted() {
        let mut r = SmpReceiver::new();
        let mut payload = Vec::new();
        payload.extend_from_slice(&[SMP_OP_READ_RSP, 0, 0, 0, 0, 0, 0, 0]);
        payload.extend_from_slice(b"hi");
        payload.extend_from_slice(&[0, 0]); // CRC placeholder
        feed_frame(&mut r, &body(payload.len() as u16, &payload), true);

        assert!(matches!(r.msg_type, Some(MsgType::Echo)));
        let data_start = MSG_HEADER_SIZE + SMP_HEADER_SIZE;
        let data_end = r.rx_msg_len - MSG_FOOTER_SIZE;
        assert_eq!(&r.rx_msg[data_start..data_end], b"hi");
    }
}
