use crate::alternating_bit::SyncBits;
use crate::header::Header;
use crate::{
    crc32::{CHECKSUM_LEN, Crc32},
    error::{Error, Result},
};

pub struct Fragmenter {
    header: Header,
    sync_bits: SyncBits,
    offset: usize,
    checksum: Crc32,
    crc_offset: usize,
}

impl Fragmenter {
    pub fn new(header: Header, sync_bits: SyncBits, payload: &[u8]) -> Result<Self> {
        if payload.len() + CHECKSUM_LEN != header.payload_len().into() {
            return Err(Error::UnexpectedInput);
        }
        Ok(Self {
            header,
            sync_bits,
            offset: 0,
            checksum: Crc32::new(),
            crc_offset: 0,
        })
    }

    pub fn next(&mut self, payload: &[u8], dest: &mut [u8], is_host: bool) -> Result<bool> {
        const MIN_PACKET_SIZE: usize = Header::new_ack(0).header_len() + 1;
        if dest.len() < MIN_PACKET_SIZE {
            return Err(Error::InsufficientBuffer);
        }
        if payload.len() + CHECKSUM_LEN != self.header.payload_len().into() {
            // buffer changed since new
            return Err(Error::UnexpectedInput);
        }
        if self.is_done() {
            return Ok(false);
        }

        let header_len = if self.offset == 0 {
            let header_len = self
                .header
                .to_bytes(self.sync_bits, dest, is_host)
                .ok_or(Error::UnexpectedInput)?;
            self.checksum.update(&dest[..header_len]);
            header_len
        } else {
            let cont_header = Header::new_continuation(self.header.channel_id());
            cont_header
                .to_bytes(SyncBits::new(), dest, is_host)
                .ok_or(Error::UnexpectedInput)?
        };
        let mut rest = &mut dest[header_len..];

        if self.offset < payload.len() {
            let source = &payload[self.offset..];
            let nbytes = source.len().min(rest.len());
            rest[..nbytes].copy_from_slice(&source[..nbytes]);
            self.checksum.update(&source[..nbytes]);
            self.offset += nbytes;
            rest = &mut rest[nbytes..];
        }

        if self.offset >= payload.len() && self.crc_offset < CHECKSUM_LEN {
            let crc = self.checksum.finalize();
            let crc = crc.get(self.crc_offset..).ok_or(Error::UnexpectedInput)?;
            let nbytes = crc.len().min(rest.len());
            rest[..nbytes].copy_from_slice(&crc[..nbytes]);
            self.crc_offset += nbytes;
            rest = &mut rest[nbytes..];
        }

        rest.fill(0u8); // zero-pad last fragment
        Ok(true)
    }

    pub fn is_done(&self) -> bool {
        let payload_done = self.offset + CHECKSUM_LEN >= self.header.payload_len().into();
        let crc_done = self.crc_offset >= CHECKSUM_LEN;
        payload_done && crc_done
    }

    /// Shortcut to serialize packet into buffer known to be large enough.
    pub fn single(
        header: Header,
        sb: SyncBits,
        payload: &[u8],
        dest: &mut [u8],
        is_host: bool,
    ) -> Result<()> {
        let mut fragmenter = Fragmenter::new(header, sb, payload)?;
        fragmenter.next(payload, dest, is_host)?;
        if !fragmenter.is_done() {
            return Err(Error::InsufficientBuffer);
        }
        Ok(())
    }
}

pub struct Reassembler {
    header: Header,
    offset: usize,
    checksum: Crc32,
}

impl Reassembler {
    pub fn new(input: &[u8], buffer: &mut [u8], is_host: bool) -> Result<Self> {
        let (header, after_header) = Header::parse(input, is_host)?;
        if header.is_continuation() {
            return Err(Error::UnexpectedInput);
        }

        let payload_len = header.payload_len().into();
        if buffer.len() < payload_len {
            return Err(Error::InsufficientBuffer);
        }

        let mut checksum = Crc32::new();
        checksum.update(&input[..header.header_len()]);

        let nbytes = after_header.len(); // Header::parse strips padding
        buffer[..nbytes].copy_from_slice(after_header);

        let checksum_bytes = (payload_len - CHECKSUM_LEN).min(nbytes);
        checksum.update(&after_header[..checksum_bytes]);

        Ok(Self {
            header,
            offset: nbytes,
            checksum,
        })
    }

    pub fn update(&mut self, input: &[u8], buffer: &mut [u8], is_host: bool) -> Result<()> {
        let (header, after_header) = Header::parse(input, is_host)?;
        if !header.is_continuation() {
            return Err(Error::UnexpectedInput);
        }

        if header.channel_id() != self.header.channel_id() {
            return Err(Error::OutOfBounds);
        }

        let payload_len = self.header.payload_len().into();
        if buffer.len() < payload_len {
            return Err(Error::InsufficientBuffer); // buffer changed since new()
        }
        let payload_remaining = payload_len.saturating_sub(self.offset);

        let nbytes = after_header.len().min(payload_remaining); // there can be padding
        buffer[self.offset..self.offset + nbytes].copy_from_slice(&after_header[..nbytes]);

        let checksum_bytes = payload_remaining.saturating_sub(CHECKSUM_LEN).min(nbytes);
        self.checksum.update(&after_header[..checksum_bytes]);

        self.offset += nbytes;
        Ok(())
    }

    pub fn is_done(&self) -> bool {
        self.offset >= self.header.payload_len().into()
    }

    pub fn verify(&self, buffer: &[u8]) -> Result<usize> {
        if !self.is_done() {
            return Err(Error::InvalidDigest);
        }
        let computed_checksum = self.checksum.finalize();
        let length_no_checksum =
            usize::from(self.header.payload_len()).saturating_sub(CHECKSUM_LEN);
        let received_checksum = *buffer
            .get(length_no_checksum..)
            .ok_or(Error::InvalidDigest)?
            .first_chunk::<CHECKSUM_LEN>()
            .ok_or(Error::InvalidDigest)?;
        if computed_checksum != received_checksum {
            return Err(Error::InvalidDigest);
        }
        Ok(length_no_checksum)
    }

    pub fn header(&self) -> Header {
        self.header.clone()
    }

    // Shortcut to deserialize single packet message.
    pub fn single<'a>(
        buffer: &[u8],
        dest: &'a mut [u8],
        is_host: bool,
    ) -> Result<(Header, &'a [u8])> {
        let reassembler = Reassembler::new(buffer, dest, is_host)?;
        if !reassembler.is_done() {
            return Err(Error::MalformedData);
        }
        let reply_len = reassembler.verify(dest)?;
        let header = reassembler.header;
        Ok((header, &dest[..reply_len]))
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use heapless::Vec;

    const MAX_FRAGMENTS: usize = 256;
    const MAX_PACKET: usize = 128;
    const MAX_MESSAGE: usize = 8096;

    fn fragment(
        header: Header,
        sb: SyncBits,
        input: &[u8],
        packet_size: usize,
        is_host: bool,
    ) -> Vec<Vec<u8, MAX_PACKET>, MAX_FRAGMENTS> {
        let mut packets = Vec::new();
        let mut fragmenter = Fragmenter::new(header, sb, input).expect("fragmenter");
        while !fragmenter.is_done() {
            let mut packet = Vec::new();
            packet.resize(packet_size, 0u8).unwrap();
            fragmenter
                .next(input, packet.as_mut_slice(), is_host)
                .expect("next");
            packets.push(packet).unwrap();
        }
        packets
    }

    fn assemble(packets: &[Vec<u8, MAX_PACKET>], is_host: bool) -> Vec<u8, MAX_MESSAGE> {
        let mut received = Vec::new();
        received.resize(MAX_MESSAGE, 0u8).unwrap();
        let mut reassembler =
            Reassembler::new(packets[0].as_slice(), received.as_mut_slice(), is_host)
                .expect("reassembler");
        for p in packets.iter().skip(1) {
            assert!(!reassembler.is_done());
            reassembler
                .update(p.as_slice(), received.as_mut_slice(), is_host)
                .expect("update");
        }
        assert!(reassembler.is_done());
        let received_len = reassembler.verify(received.as_slice()).expect("verify");
        received.truncate(received_len);
        received
    }

    #[test]
    fn test_roundtrip() {
        const DATA: &'static [u8] = b"The Quick Brown Fox Jumps Over the Lazy Dog The Quick Brown Fox Jumps Over the Lazy Dog";
        const PACKET_SIZE: usize = 13;
        const IS_HOST: bool = false;

        for i in 0..DATA.len() {
            let source = &DATA[..i];
            let channel_id = i as u16;
            let header = Header::new_encrypted(channel_id, source);

            let packets = fragment(header, SyncBits::new(), source, PACKET_SIZE, IS_HOST);
            // println!("message len: {}, packets: {}", i, packets.len());
            // packets.iter().for_each(|p| println!("{}", hex::encode(&p)));
            let assembled = assemble(&packets, !IS_HOST);

            let expected_hex = hex::encode(source);
            let received_hex = hex::encode(assembled.as_slice());
            assert_eq!(received_hex, expected_hex);
        }
    }

    // follwing vectors and tests adapted from test_trezor.wire.thp.writer.py

    const EMPTY_PAYLOAD_EXPECTED: &str = "0412340004edbd479c00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000";
    const SHORT_PAYLOAD_EXPECTED: &str = "041234000507ac292947000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000";
    const LONGER_PAYLOAD_EXPECTED: &[&str] = &[
        "0412340104000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a",
        "8012343b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f7071727374757677",
        "80123478797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4",
        "801234b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1",
        "801234f2f3f4f5f6f7f8f9fafbfcfdfeffc5ecc4ca00000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
    ];
    const EVEN_LONGER_PAYLOADS_EXPECTED: &[&str] = &[
        "0412340804000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a",
        "8012343b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f7071727374757677",
        "80123478797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4",
        "801234b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1",
        "801234f2f3f4f5f6f7f8f9fafbfcfdfeff000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e",
        "8012342f303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b",
        "8012346c6d6e6f707172737475767778797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8",
        "801234a9aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5",
        "801234e6e7e8e9eaebecedeeeff0f1f2f3f4f5f6f7f8f9fafbfcfdfeff000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122",
        "801234232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f",
        "801234606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c",
        "8012349d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9",
        "801234dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1f2f3f4f5f6f7f8f9fafbfcfdfeff000102030405060708090a0b0c0d0e0f10111213141516",
        "8012341718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f50515253",
        "8012345455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f90",
        "8012349192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccd",
        "801234cecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1f2f3f4f5f6f7f8f9fafbfcfdfeff000102030405060708090a",
        "8012340b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f4041424344454647",
        "80123448494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f8081828384",
        "80123485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebfc0c1",
        "801234c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1f2f3f4f5f6f7f8f9fafbfcfdfe",
        "801234ff000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b",
        "8012343c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f707172737475767778",
        "801234797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4b5",
        "801234b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1f2",
        "801234f3f4f5f6f7f8f9fafbfcfdfeff000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f",
        "801234303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c",
        "8012346d6e6f707172737475767778797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9",
        "801234aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6",
        "801234e7e8e9eaebecedeeeff0f1f2f3f4f5f6f7f8f9fafbfcfdfeff000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20212223",
        "8012342425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f60",
        "8012346162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d",
        "8012349e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9da",
        "801234dbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1f2f3f4f5f6f7f8f9fafbfcfdfeff13fe4cae0000000000000000000000000000000000000000",
    ];

    const PACKET_LEN: usize = 64;
    const CHANNEL_ID: u16 = 4660;

    #[test]
    fn test_write_empty_payload() {
        let header = Header::new_encrypted(CHANNEL_ID, &[]);
        let packets = fragment(header, SyncBits::new(), &[], PACKET_LEN, false);
        assert_eq!(packets.len(), 1);
        assert_eq!(hex::encode(&packets[0]), EMPTY_PAYLOAD_EXPECTED);
    }

    #[test]
    fn test_write_short_payload() {
        let data = &[0x07];
        let header = Header::new_encrypted(CHANNEL_ID, data);
        let packets = fragment(header, SyncBits::new(), data, PACKET_LEN, false);
        assert_eq!(packets.len(), 1);
        assert_eq!(hex::encode(&packets[0]), SHORT_PAYLOAD_EXPECTED);
    }

    #[test]
    fn test_write_longer_payload() {
        let data: Vec<u8, 256> = (0..=255).collect();
        let header = Header::new_encrypted(CHANNEL_ID, &data);
        let packets = fragment(header, SyncBits::new(), &data, PACKET_LEN, false);
        assert_eq!(packets.len(), LONGER_PAYLOAD_EXPECTED.len());
        packets
            .iter()
            .zip(LONGER_PAYLOAD_EXPECTED)
            .for_each(|(got, expected)| assert_eq!(&hex::encode(got), expected));
    }

    #[test]
    fn test_write_even_longer_payload() {
        let data: Vec<u8, 2048> = (0..2048u16)
            .map(|n| u8::try_from(n & 0xff).unwrap())
            .collect();
        let header = Header::new_encrypted(CHANNEL_ID, &data);
        let packets = fragment(header, SyncBits::new(), &data, PACKET_LEN, false);
        assert_eq!(packets.len(), EVEN_LONGER_PAYLOADS_EXPECTED.len());
        packets
            .iter()
            .zip(EVEN_LONGER_PAYLOADS_EXPECTED)
            .for_each(|(got, expected)| assert_eq!(&hex::encode(got), expected));
    }
}
