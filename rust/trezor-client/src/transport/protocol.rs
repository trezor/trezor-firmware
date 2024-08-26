use crate::{
    protos::MessageType,
    transport::{error::Error, ProtoMessage},
};
use byteorder::{BigEndian, ByteOrder};
use protobuf::Enum;
use std::cmp;

/// A link represents a serial connection to send and receive byte chunks from and to a device.
pub trait Link {
    fn write_chunk(&mut self, chunk: Vec<u8>) -> Result<(), Error>;
    fn read_chunk(&mut self) -> Result<Vec<u8>, Error>;
}

/// A protocol is used to encode messages in chunks that can be sent to the device and to parse
/// chunks into messages.
pub trait Protocol {
    fn session_begin(&mut self) -> Result<(), Error>;
    fn session_end(&mut self) -> Result<(), Error>;
    fn write(&mut self, message: ProtoMessage) -> Result<(), Error>;
    fn read(&mut self) -> Result<ProtoMessage, Error>;
}

/// The length of the chunks sent.
const REPLEN: usize = 64;

/// V2 of the binary protocol.
/// This version is currently not in use by any device and is subject to change.
#[allow(dead_code)]
pub struct ProtocolV2<L: Link> {
    pub link: L,
    pub session_id: u32,
}

impl<L: Link> Protocol for ProtocolV2<L> {
    fn session_begin(&mut self) -> Result<(), Error> {
        let mut chunk = vec![0; REPLEN];
        chunk[0] = 0x03;
        self.link.write_chunk(chunk)?;
        let resp = self.link.read_chunk()?;
        if resp[0] != 0x03 {
            println!("bad magic in v2 session_begin: {:x} instead of 0x03", resp[0]);
            return Err(Error::DeviceBadMagic);
        }
        self.session_id = BigEndian::read_u32(&resp[1..5]);
        Ok(())
    }

    fn session_end(&mut self) -> Result<(), Error> {
        assert!(self.session_id != 0);
        let mut chunk = vec![0; REPLEN];
        chunk[0] = 0x04;
        BigEndian::write_u32(&mut chunk[1..5], self.session_id);
        self.link.write_chunk(chunk)?;
        let resp = self.link.read_chunk()?;
        if resp[0] != 0x04 {
            println!("bad magic in v2 session_end: {:x} instead of 0x04", resp[0]);
            return Err(Error::DeviceBadMagic);
        }
        self.session_id = 0;
        Ok(())
    }

    fn write(&mut self, message: ProtoMessage) -> Result<(), Error> {
        assert!(self.session_id != 0);

        // First generate the total payload, then write it to the transport in chunks.
        let mut data = vec![0; 8];
        BigEndian::write_u32(&mut data[0..4], message.message_type() as u32);
        BigEndian::write_u32(&mut data[4..8], message.payload().len() as u32);
        data.extend(message.into_payload());

        let mut cur: usize = 0;
        let mut seq: isize = -1;
        while cur < data.len() {
            // Build header.
            let mut chunk = if seq < 0 {
                let mut header = vec![0; 5];
                header[0] = 0x01;
                BigEndian::write_u32(&mut header[1..5], self.session_id);
                header
            } else {
                let mut header = vec![0; 9];
                header[0] = 0x01;
                BigEndian::write_u32(&mut header[1..5], self.session_id);
                BigEndian::write_u32(&mut header[5..9], seq as u32);
                header
            };
            seq += 1;

            // Fill remainder.
            let end = cmp::min(cur + (REPLEN - chunk.len()), data.len());
            chunk.extend(&data[cur..end]);
            cur = end;
            debug_assert!(chunk.len() <= REPLEN);
            chunk.resize(REPLEN, 0);

            self.link.write_chunk(chunk)?;
        }

        Ok(())
    }

    fn read(&mut self) -> Result<ProtoMessage, Error> {
        debug_assert!(self.session_id != 0);

        let chunk = self.link.read_chunk()?;
        if chunk[0] != 0x01 {
            println!("bad magic in v2 read: {:x} instead of 0x01", chunk[0]);
            return Err(Error::DeviceBadMagic);
        }
        if BigEndian::read_u32(&chunk[1..5]) != self.session_id {
            return Err(Error::DeviceBadSessionId);
        }
        let message_type_id = BigEndian::read_u32(&chunk[5..9]);
        let message_type = MessageType::from_i32(message_type_id as i32)
            .ok_or(Error::InvalidMessageType(message_type_id))?;
        let data_length = BigEndian::read_u32(&chunk[9..13]) as usize;

        let mut data: Vec<u8> = chunk[13..].into();
        let mut seq = 0;
        while data.len() < data_length {
            let chunk = self.link.read_chunk()?;
            if chunk[0] != 0x02 {
                println!("bad magic in v2 session_begin: {:x} instead of 0x02", chunk[0]);
                return Err(Error::DeviceBadMagic);
            }
            if BigEndian::read_u32(&chunk[1..5]) != self.session_id {
                return Err(Error::DeviceBadSessionId);
            }
            if BigEndian::read_u32(&chunk[5..9]) != seq as u32 {
                return Err(Error::DeviceUnexpectedSequenceNumber);
            }
            seq += 1;

            data.extend(&chunk[9..]);
        }

        Ok(ProtoMessage(message_type, data[0..data_length].into()))
    }
}

/// The original binary protocol.
pub struct ProtocolV1<L: Link> {
    pub link: L,
}

impl<L: Link> Protocol for ProtocolV1<L> {
    fn session_begin(&mut self) -> Result<(), Error> {
        Ok(()) // no sessions
    }

    fn session_end(&mut self) -> Result<(), Error> {
        Ok(()) // no sessions
    }

    fn write(&mut self, message: ProtoMessage) -> Result<(), Error> {
        // First generate the total payload, then write it to the transport in chunks.
        let mut data = vec![0; 8];
        data[0] = 0x23;
        data[1] = 0x23;
        BigEndian::write_u16(&mut data[2..4], message.message_type() as u16);
        BigEndian::write_u32(&mut data[4..8], message.payload().len() as u32);
        data.extend(message.into_payload());

        let mut cur: usize = 0;
        while cur < data.len() {
            let mut chunk = vec![0x3f];
            let end = cmp::min(cur + (REPLEN - 1), data.len());
            chunk.extend(&data[cur..end]);
            cur = end;
            debug_assert!(chunk.len() <= REPLEN);
            chunk.resize(REPLEN, 0);

            self.link.write_chunk(chunk)?;
        }

        Ok(())
    }

    fn read(&mut self) -> Result<ProtoMessage, Error> {
        let chunk = self.link.read_chunk()?;
        if chunk[0] != 0x3f || chunk[1] != 0x23 || chunk[2] != 0x23 {
            println!(
                "bad magic in v1 read: {:x}{:x}{:x} instead of 0x3f2323",
                chunk[0], chunk[1], chunk[2]
            );
            return Err(Error::DeviceBadMagic);
        }
        let message_type_id = BigEndian::read_u16(&chunk[3..5]) as u32;
        let message_type = MessageType::from_i32(message_type_id as i32)
            .ok_or(Error::InvalidMessageType(message_type_id))?;
        let data_length = BigEndian::read_u32(&chunk[5..9]) as usize;
        let mut data: Vec<u8> = chunk[9..].into();

        while data.len() < data_length {
            let chunk = self.link.read_chunk()?;
            if chunk[0] != 0x3f {
                println!("bad magic in v1 read: {:x} instead of 0x3f", chunk[0]);
                return Err(Error::DeviceBadMagic);
            }

            data.extend(&chunk[1..]);
        }

        Ok(ProtoMessage(message_type, data[0..data_length].into()))
    }
}
