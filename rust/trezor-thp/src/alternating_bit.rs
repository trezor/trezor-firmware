use crate::control_byte::{ACK_BIT, SEQ_BIT};

#[derive(Clone, Copy)]
pub struct SyncBits(u8);

impl SyncBits {
    pub const fn new() -> Self {
        Self(0u8)
    }

    pub const fn seq_bit(&self) -> bool {
        (self.0 & SEQ_BIT) != 0
    }

    pub const fn ack_bit(&self) -> bool {
        (self.0 & ACK_BIT) != 0
    }

    pub const fn with_seq_bit(self, seq_bit: bool) -> Self {
        Self(if seq_bit {
            self.0 | SEQ_BIT
        } else {
            self.0 & !SEQ_BIT
        })
    }

    pub const fn with_ack_bit(self, ack_bit: bool) -> Self {
        Self(if ack_bit {
            self.0 | ACK_BIT
        } else {
            self.0 & !ACK_BIT
        })
    }
}

impl From<u8> for SyncBits {
    fn from(byte: u8) -> Self {
        Self(byte)
    }
}

impl From<SyncBits> for u8 {
    fn from(sb: SyncBits) -> Self {
        sb.0
    }
}

impl Default for SyncBits {
    fn default() -> Self {
        Self::new()
    }
}

/// Alternating Bit Protocol state for a single channel.
pub struct ChannelSync<T> {
    /// Stores timestamp of the last sent message that hasn't been ACKed.
    /// None means no message in transit, meaning our side can send.
    last_send: Option<T>,
    /// Send bit.
    sync_send: bool,
    /// Receive bit.
    sync_receive: bool,
    /// Preparation for https://github.com/trezor/trezor-firmware/issues/6135
    ack_piggybacking: bool,
}

impl<T: Default> ChannelSync<T> {
    pub fn new() -> Self {
        Self {
            last_send: None,
            sync_send: false,
            sync_receive: false,
            ack_piggybacking: false,
        }
    }

    /// Returns false if we're waiting for an ACK.
    pub fn can_send(&self) -> bool {
        self.last_send.is_none()
    }

    /// Call before sending a message.
    /// Returns none if the previous transmission hasn't finished yet.
    /// If we can send returns SyncBits to be used when serializing message.
    pub fn send_start(&mut self) -> Option<SyncBits> {
        if self.last_send.is_some() {
            return None; // sending in progress, don't send
        }

        let sb = SyncBits::new().with_seq_bit(self.sync_send);
        Some(sb) // start sending, use these bits
    }

    /// Call after sending last message fragment.
    /// Save timestamp and wait for ACK before allowing next message.
    pub fn send_finish(&mut self, timestamp: T) {
        self.last_send = Some(timestamp);
    }

    /// Call after receiving an ACK message.
    pub fn send_mark_delivered(&mut self, sb: SyncBits) {
        if self.sync_send == sb.ack_bit() {
            self.sync_send = !self.sync_send;
            self.last_send = None;
        }
    }

    /// Call after receving initial fragment of a message.
    /// Returns true when seq_bit is correct and we should reassemble the message.
    /// If the function returns false all following continuation packets should be discarded.
    pub fn receive_start(&mut self, sb: SyncBits) -> bool {
        if sb.seq_bit() != self.sync_receive {
            // Either this message is a duplicate or previous one was dropped.
            return false;
        }

        // NOTE: consider intercepting ACKs here and passing them to send_mark_delivered
        true
    }

    /// Call after receiving last fragment and successfully verifying CRC of the message.
    /// Caller needs to send ACK with the returned SyncBits.
    pub fn receive_acknowledge(&mut self) -> Option<SyncBits> {
        let sb = SyncBits::new().with_ack_bit(self.sync_receive);
        self.sync_receive = !self.sync_receive;
        Some(sb)
    }

    /// Serialize for storage.
    /// can_send_bit | sync_receive_bit | sync_send_bit | ack_piggybacking | rfu(4)
    pub fn to_u8(&self) -> u8 {
        let mut res = 0u8;
        if self.last_send.is_none() {
            res |= 0x80;
        }
        if self.sync_receive {
            res |= 0x40;
        }
        if self.sync_send {
            res |= 0x20;
        }
        if self.ack_piggybacking {
            res |= 0x10;
        }
        res
    }

    /// Deserialize from storage.
    pub fn from_u8(val: u8) -> Self {
        let last_send = if val & 0x80 != 0 {
            None
        } else {
            Some(T::default())
        };
        Self {
            sync_send: (val & 0x20 != 0),
            sync_receive: (val & 0x40 != 0),
            last_send,
            ack_piggybacking: (val & 0x10 != 0),
        }
    }
}

impl<T: Default> Default for ChannelSync<T> {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use core::sync::atomic::{AtomicU32, Ordering};

    fn ts() -> u32 {
        static COUNTER: AtomicU32 = AtomicU32::new(0);
        COUNTER.fetch_add(1, Ordering::Relaxed)
    }

    #[test]
    fn test_simple_rt() {
        let mut host_sync = ChannelSync::<u32>::new();
        let mut trezor_sync = ChannelSync::<u32>::new();

        // request
        assert!(host_sync.can_send());
        let sb = host_sync.send_start().unwrap();
        assert_eq!(sb.seq_bit(), false);
        host_sync.send_finish(ts());
        assert!(!host_sync.can_send());
        // H->T
        let ok = trezor_sync.receive_start(sb);
        assert!(ok);
        let sb = trezor_sync.receive_acknowledge().unwrap();
        assert_eq!(sb.ack_bit(), false);
        // T->H ACK
        host_sync.send_mark_delivered(sb);
        assert!(host_sync.can_send());

        // reply
        assert!(trezor_sync.can_send());
        let sb = trezor_sync.send_start().unwrap();
        assert_eq!(sb.seq_bit(), false);
        trezor_sync.send_finish(ts());
        assert!(!trezor_sync.can_send());
        // T->H
        let ok = host_sync.receive_start(sb);
        assert!(ok);
        let sb = host_sync.receive_acknowledge().unwrap();
        assert_eq!(sb.ack_bit(), false);
        // H->T ACK
        trezor_sync.send_mark_delivered(sb);
        assert!(trezor_sync.can_send());

        // confirm alternation
        assert_eq!(host_sync.send_start().unwrap().seq_bit(), true);
        assert_eq!(trezor_sync.send_start().unwrap().seq_bit(), true);
    }

    #[test]
    fn test_oneway() {
        let mut a_sync = ChannelSync::<u32>::new();
        let mut b_sync = ChannelSync::<u32>::new();

        for i in 0..32 {
            let expected: bool = i % 2 != 0;
            assert!(a_sync.can_send());
            let sb = a_sync.send_start().unwrap();
            a_sync.send_finish(ts());
            assert_eq!(sb.seq_bit(), expected);
            assert!(!a_sync.can_send());
            assert!(b_sync.receive_start(sb));
            let sb = b_sync.receive_acknowledge().unwrap();
            assert_eq!(sb.ack_bit(), expected);
            a_sync.send_mark_delivered(sb);
            assert!(a_sync.can_send());
        }
    }
}
