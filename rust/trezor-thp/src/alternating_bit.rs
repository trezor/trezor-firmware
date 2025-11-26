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
#[cfg_attr(any(test, debug_assertions), derive(Debug, PartialEq))]
pub struct ChannelSync {
    /// If true we are waiting for an ACK and cannot send further messages.
    can_send: bool,
    /// Receive bit.
    sync_receive: bool,
    /// Send bit.
    sync_send: bool,
    /// Preparation for https://github.com/trezor/trezor-firmware/issues/6135
    ack_piggybacking: bool,
}

impl ChannelSync {
    pub fn new() -> Self {
        Self {
            can_send: true,
            sync_receive: false,
            sync_send: false,
            ack_piggybacking: false,
        }
    }

    /// Returns false if we're waiting for an ACK.
    pub fn can_send(&self) -> bool {
        self.can_send
    }

    /// Call before sending a message.
    /// Returns none if the previous transmission hasn't finished yet.
    /// If we can send returns SyncBits to be used when serializing message.
    pub fn send_start(&self) -> Option<SyncBits> {
        if !self.can_send() {
            return None; // sending in progress, don't send
        }

        let sb = SyncBits::new().with_seq_bit(self.sync_send);
        Some(sb) // start sending, use these bits
    }

    /// Call after sending last message fragment, wait for ACK before allowing next message.
    /// NOTE: Consider saving some kind of timestamp or identifier instead of bool.
    pub fn send_finish(&mut self) {
        self.can_send = false;
    }

    /// Call after receiving an ACK message.
    pub fn send_mark_delivered(&mut self, sb: SyncBits) {
        if self.sync_send == sb.ack_bit() {
            self.sync_send.increment();
            self.can_send = true;
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
    pub fn receive_acknowledge(&mut self) -> SyncBits {
        let sb = SyncBits::new().with_ack_bit(self.sync_receive);
        self.sync_receive.increment();
        sb
    }

    /// Serialize for storage.
    /// can_send_bit | sync_receive_bit | sync_send_bit | ack_piggybacking | rfu(4)
    pub fn to_u8(&self) -> u8 {
        let mut res = 0u8;
        if self.can_send {
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
        Self {
            can_send: (val & 0x80 != 0),
            sync_receive: (val & 0x40 != 0),
            sync_send: (val & 0x20 != 0),
            ack_piggybacking: (val & 0x10 != 0),
        }
    }
}

impl Default for ChannelSync {
    fn default() -> Self {
        Self::new()
    }
}

trait BoolExt {
    fn increment(&mut self);
}

impl BoolExt for bool {
    fn increment(&mut self) {
        *self = !*self;
    }
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn test_simple_rt() {
        let mut host_sync = ChannelSync::new();
        let mut trezor_sync = ChannelSync::new();

        // request
        assert!(host_sync.can_send());
        let sb = host_sync.send_start().unwrap();
        assert_eq!(sb.seq_bit(), false);
        host_sync.send_finish();
        assert!(!host_sync.can_send());
        // H->T
        let ok = trezor_sync.receive_start(sb);
        assert!(ok);
        let sb = trezor_sync.receive_acknowledge();
        assert_eq!(sb.ack_bit(), false);
        // T->H ACK
        host_sync.send_mark_delivered(sb);
        assert!(host_sync.can_send());

        // reply
        assert!(trezor_sync.can_send());
        let sb = trezor_sync.send_start().unwrap();
        assert_eq!(sb.seq_bit(), false);
        trezor_sync.send_finish();
        assert!(!trezor_sync.can_send());
        // T->H
        let ok = host_sync.receive_start(sb);
        assert!(ok);
        let sb = host_sync.receive_acknowledge();
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
        let mut a_sync = ChannelSync::new();
        let mut b_sync = ChannelSync::new();

        for i in 0..32 {
            let expected: bool = i % 2 != 0;
            assert!(a_sync.can_send());
            let sb = a_sync.send_start().unwrap();
            a_sync.send_finish();
            assert_eq!(sb.seq_bit(), expected);
            assert!(!a_sync.can_send());
            assert!(b_sync.receive_start(sb));
            let sb = b_sync.receive_acknowledge();
            assert_eq!(sb.ack_bit(), expected);
            a_sync.send_mark_delivered(sb);
            assert!(a_sync.can_send());
        }
    }

    #[test]
    fn test_serialize_rt() {
        for cs in 0..1 {
            for sr in 0..1 {
                for ss in 0..1 {
                    for ap in 0..1 {
                        let orig = ChannelSync {
                            can_send: cs != 0,
                            sync_receive: sr != 0,
                            sync_send: ss != 0,
                            ack_piggybacking: ap != 0,
                        };
                        assert_eq!(ChannelSync::from_u8(orig.to_u8()), orig);
                        assert_eq!(ChannelSync::from_u8(orig.to_u8()).to_u8(), orig.to_u8());
                    }
                }
            }
        }
    }

    #[test]
    fn test_serialize_rfu() {
        let orig = ChannelSync::from_u8(0);
        for u in 0..0x0fu8 {
            assert_eq!(ChannelSync::from_u8(u), orig);
        }
    }

    #[test]
    fn test_serialize_simple() {
        let mut sync = ChannelSync::new();
        assert_eq!(sync.to_u8(), 0b10000000); // can_send=true
        sync.send_finish();
        assert_eq!(sync.to_u8(), 0b00000000);
        sync.send_mark_delivered(SyncBits::new());
        assert_eq!(sync.to_u8(), 0b10100000);
        sync.receive_start(SyncBits::new());
        sync.receive_acknowledge();
        assert_eq!(sync.to_u8(), 0b11100000);
    }
}
