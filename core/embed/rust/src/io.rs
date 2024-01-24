use crate::error::Error;

pub struct InputStream<'a> {
    buf: &'a [u8],
    pos: usize,
}

impl<'a> InputStream<'a> {
    pub fn new(buf: &'a [u8]) -> Self {
        Self { buf, pos: 0 }
    }

    pub fn remaining(&self) -> usize {
        self.buf.len().saturating_sub(self.pos)
    }

    pub fn tell(&self) -> usize {
        self.pos
    }

    pub fn read_stream(&mut self, len: usize) -> Result<Self, Error> {
        self.read(len).map(Self::new)
    }

    pub fn read(&mut self, len: usize) -> Result<&'a [u8], Error> {
        let buf = self
            .buf
            .get(self.pos..self.pos + len)
            .ok_or(Error::EOFError)?;
        self.pos += len;
        Ok(buf)
    }

    pub fn rest(self) -> &'a [u8] {
        if self.pos > self.buf.len() {
            &[]
        } else {
            &self.buf[self.pos..]
        }
    }

    pub fn read_byte(&mut self) -> Result<u8, Error> {
        let val = self.buf.get(self.pos).ok_or(Error::EOFError)?;
        self.pos += 1;
        Ok(*val)
    }

    pub fn read_u16_le(&mut self) -> Result<u16, Error> {
        let buf = self.read(2)?;
        Ok(u16::from_le_bytes(unwrap!(buf.try_into())))
    }

    pub fn read_u32_le(&mut self) -> Result<u32, Error> {
        let buf = self.read(4)?;
        Ok(u32::from_le_bytes(unwrap!(buf.try_into())))
    }

    pub fn read_uvarint(&mut self) -> Result<u64, Error> {
        let mut uint = 0;
        let mut shift = 0;
        loop {
            let byte = self.read_byte()?;
            uint += (byte as u64 & 0x7F) << shift;
            shift += 7;
            if byte & 0x80 == 0 {
                break;
            }
        }
        Ok(uint)
    }
}
