use crate::error::Error;

#[cfg(feature = "micropython")]
use crate::micropython::{buffer::get_buffer, gc::Gc, obj::Obj};

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

#[derive(Copy, Clone)]
pub enum BinaryData<'a> {
    Slice(&'a [u8]),
    #[cfg(feature = "micropython")]
    Object(Obj),
    #[cfg(feature = "micropython")]
    AllocatedSlice(Gc<[u8]>),
}

impl<'a> BinaryData<'a> {
    /// Returns `true` if the binary data is empty.
    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    /// Returns a reference to the binary data.
    ///
    /// This function is used just in the `paint()` functions in
    /// UI components, that are going to be deleted after adopting new
    /// drawing library for models T and TS3. Do not use this function in new
    /// code.
    ///
    /// # Safety
    /// The caller must ensure that the returned slice is not modified by
    /// MicroPython. This means (a) discarding the slice before returning
    /// to Python, and (b) being careful about calling into Python while
    /// the slice is held.
    pub unsafe fn data(&self) -> &[u8] {
        match self {
            Self::Slice(data) => data,
            // SAFETY: We expect no existing mutable reference. See safety
            // note above.
            #[cfg(feature = "micropython")]
            Self::Object(obj) => unsafe { unwrap!(get_buffer(*obj)) },
            #[cfg(feature = "micropython")]
            Self::AllocatedSlice(data) => data,
        }
    }

    /// Returns the length of the binary data in bytes.
    pub fn len(&self) -> usize {
        match self {
            Self::Slice(data) => data.len(),
            #[cfg(feature = "micropython")]
            // SAFETY: We expect no existing mutable reference.
            Self::Object(obj) => unsafe { unwrap!(get_buffer(*obj)).len() },
            #[cfg(feature = "micropython")]
            Self::AllocatedSlice(data) => data.len(),
        }
    }

    /// Reads binary data from the source into the buffer.
    /// - 'ofs' is the offset in bytes from the start of the binary data.
    /// - 'buff' is the buffer to read the data into.
    ///
    /// Returns the number of bytes read.
    pub fn read(&self, ofs: usize, buff: &mut [u8]) -> usize {
        match self {
            Self::Slice(data) => {
                let remaining = data.len().saturating_sub(ofs);
                let size = buff.len().min(remaining);
                buff[..size].copy_from_slice(&data[ofs..ofs + size]);
                size
            }

            // SAFETY: We expect no existing mutable reference to `obj`.
            #[cfg(feature = "micropython")]
            Self::Object(obj) => {
                let data = unsafe { unwrap!(get_buffer(*obj)) };
                let remaining = data.len().saturating_sub(ofs);
                let size = buff.len().min(remaining);
                buff[..size].copy_from_slice(&data[ofs..ofs + size]);
                size
            }

            #[cfg(feature = "micropython")]
            Self::AllocatedSlice(data) => {
                let remaining = data.len().saturating_sub(ofs);
                let size = buff.len().min(remaining);
                buff[..size].copy_from_slice(&data[ofs..ofs + size]);
                size
            }
        }
    }
}

impl<'a> PartialEq for BinaryData<'a> {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (Self::Slice(a), Self::Slice(b)) => a.as_ptr() == b.as_ptr() && a.len() == b.len(),
            #[cfg(feature = "micropython")]
            (Self::Object(a), Self::Object(b)) => a == b,
            #[cfg(feature = "micropython")]
            (Self::AllocatedSlice(a), Self::AllocatedSlice(b)) => {
                a.as_ptr() == b.as_ptr() && a.len() == b.len()
            }
            #[cfg(feature = "micropython")]
            _ => false,
        }
    }
}

#[cfg(feature = "micropython")]
impl From<Gc<[u8]>> for BinaryData<'static> {
    fn from(data: Gc<[u8]>) -> Self {
        Self::AllocatedSlice(data)
    }
}

#[cfg(feature = "micropython")]
impl TryFrom<Obj> for BinaryData<'static> {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        if !obj.is_bytes() {
            return Err(Error::TypeError);
        }
        Ok(Self::Object(obj))
    }
}

impl<'a> From<&'a [u8]> for BinaryData<'a> {
    fn from(data: &'a [u8]) -> Self {
        Self::Slice(data)
    }
}
