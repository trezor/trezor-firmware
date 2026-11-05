//! RootPacket: the Merkle roots of the app rings, signed by the vendor keys.
//! Byte layout as in `trezorlib.root_packet`.

pub const MAX_RINGS: usize = 3;
pub const NUM_SIGNATURES: usize = 2;

const MAGIC: &[u8; 4] = b"TRRP";
const VERSION: u8 = 1;
const SIGMASK: u8 = 0b11;
const SIGNATURE_LEN: usize = 2420;

pub struct RootPacket {
    ring_mask: u8,
    timestamp: i64,
    chain_timestamp: i64,
    root_rings: Vec<[u8; 32]>,
    signatures: [[u8; SIGNATURE_LEN]; NUM_SIGNATURES],
}

impl RootPacket {
    /// `root_rings` are `(ring, root)` pairs in ascending ring order.
    pub fn new(root_rings: &[(u8, [u8; 32])], timestamp: i64) -> Self {
        let includes_ring0 = root_rings.iter().any(|&(ring, _)| ring == 0);
        RootPacket {
            ring_mask: root_rings
                .iter()
                .fold(0, |mask, &(ring, _)| mask | 1 << ring),
            timestamp,
            chain_timestamp: if includes_ring0 { 0 } else { timestamp },
            root_rings: root_rings.iter().map(|&(_, root)| root).collect(),
            signatures: [[0; SIGNATURE_LEN]; NUM_SIGNATURES],
        }
    }

    pub fn root_rings(&self) -> &[[u8; 32]] {
        &self.root_rings
    }

    /// The part covered by the signatures.
    fn auth_bytes(&self) -> Vec<u8> {
        let mut bytes = Vec::new();
        bytes.extend_from_slice(MAGIC);
        bytes.push(VERSION);
        bytes.push(self.ring_mask);
        bytes.extend_from_slice(&[0; 2]); // reserved
        bytes.extend_from_slice(&self.timestamp.to_le_bytes());
        bytes.extend_from_slice(&self.chain_timestamp.to_le_bytes());
        for root in &self.root_rings {
            bytes.extend_from_slice(root);
        }
        bytes
    }

    /// Serializes the packet with zeroed signatures.
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut bytes = self.auth_bytes();
        bytes.push(SIGMASK);
        bytes.extend_from_slice(&[0; 3]); // reserved
        for signature in &self.signatures {
            bytes.extend_from_slice(signature);
        }
        bytes
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const AUTH_HEADER_LEN: usize = 4 + 1 + 1 + 2 + 8 + 8;
    const UNAUTH_LEN: usize = 1 + 3 + NUM_SIGNATURES * SIGNATURE_LEN;

    #[test]
    fn ring0_packet_layout() {
        let bytes = RootPacket::new(&[(0, [0xaa; 32])], 0x0102).to_bytes();
        assert_eq!(bytes.len(), AUTH_HEADER_LEN + 32 + UNAUTH_LEN);
        assert_eq!(&bytes[..4], b"TRRP");
        assert_eq!(bytes[4], VERSION);
        assert_eq!(bytes[5], 0b001);
        assert_eq!(&bytes[8..16], &0x0102i64.to_le_bytes());
        assert_eq!(&bytes[16..24], &0i64.to_le_bytes()); // chain_timestamp
        assert_eq!(&bytes[24..56], &[0xaa; 32]);
        assert_eq!(bytes[56], SIGMASK);
    }

    #[test]
    fn ring12_packet_layout() {
        let bytes = RootPacket::new(&[(1, [0; 32]), (2, [0xbb; 32])], 0x0102).to_bytes();
        assert_eq!(bytes.len(), AUTH_HEADER_LEN + 2 * 32 + UNAUTH_LEN);
        assert_eq!(bytes[5], 0b110);
        assert_eq!(&bytes[16..24], &0x0102i64.to_le_bytes()); // chain_timestamp
        assert_eq!(&bytes[24..56], &[0; 32]);
        assert_eq!(&bytes[56..88], &[0xbb; 32]);
    }
}
