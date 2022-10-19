use crate::{
    error::Error,
    micropython::{
        buffer::{get_buffer, get_str_owner, StrBuffer},
        gc::Gc,
        iter::{Iter, IterBuf},
        list::List,
        obj::Obj,
    },
    ui::component::text::{
        paragraphs::{Paragraph, ParagraphSource},
        TextStyle,
    },
};
use core::str;
use cstr_core::cstr;
use heapless::Vec;

pub fn iter_into_objs<const N: usize>(iterable: Obj) -> Result<[Obj; N], Error> {
    let err = Error::ValueError(cstr!("Invalid iterable length"));
    let mut vec = Vec::<Obj, N>::new();
    let mut iter_buf = IterBuf::new();
    for item in Iter::try_from_obj_with_buf(iterable, &mut iter_buf)? {
        vec.push(item).map_err(|_| err)?;
    }
    // Returns error if array.len() != N
    vec.into_array().map_err(|_| err)
}

pub fn iter_into_array<T, const N: usize>(iterable: Obj) -> Result<[T; N], Error>
where
    T: TryFrom<Obj, Error = Error>,
{
    let err = Error::ValueError(cstr!("Invalid iterable length"));
    let mut vec = Vec::<T, N>::new();
    let mut iter_buf = IterBuf::new();
    for item in Iter::try_from_obj_with_buf(iterable, &mut iter_buf)? {
        vec.push(item.try_into()?).map_err(|_| err)?;
    }
    // Returns error if array.len() != N
    vec.into_array().map_err(|_| err)
}

fn hexlify<'a>(data: &[u8], buffer: &'a mut [u8]) -> &'a str {
    const HEX_LOWER: [u8; 16] = *b"0123456789abcdef";
    let mut i: usize = 0;
    for b in data.iter().take(buffer.len() / 2) {
        let hi: usize = ((b & 0xf0) >> 4).into();
        let lo: usize = (b & 0x0f).into();
        buffer[i] = HEX_LOWER[hi];
        buffer[i + 1] = HEX_LOWER[lo];
        i += 2;
    }
    // SAFETY: only <0x7f bytes are used to construct the string
    unsafe { str::from_utf8_unchecked(&buffer[0..i]) }
}

pub enum StrOrBytes {
    Str(StrBuffer),
    Bytes(Obj),
}

impl StrOrBytes {
    pub fn as_str_offset<'a>(&'a self, offset: usize, buffer: &'a mut [u8]) -> &'a str {
        match self {
            StrOrBytes::Str(x) => &x.as_ref()[offset..],
            StrOrBytes::Bytes(x) => Self::hexlify(*x, offset, buffer),
        }
    }

    fn hexlify(obj: Obj, offset: usize, buffer: &mut [u8]) -> &str {
        if !obj.is_bytes() {
            return "ERROR";
        }

        // Convert offset to byte representation, handle case where it points in the
        // middle of a byte.
        let bin_off = offset / 2;
        let hex_off = offset % 2;

        // SAFETY:
        // (a) only immutable references are taken
        // (b) reference is discarded before returning to micropython
        let bin_slice = if let Ok(buf) = unsafe { get_buffer(obj) } {
            &buf[bin_off..]
        } else {
            return "ERROR";
        };
        let hexadecimal = hexlify(bin_slice, buffer);

        &hexadecimal[hex_off..]
    }
}

impl TryFrom<Obj> for StrOrBytes {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Error> {
        if obj.is_str() {
            Ok(StrOrBytes::Str(obj.try_into()?))
        } else if obj.is_bytes() {
            Ok(StrOrBytes::Bytes(obj))
        } else {
            Err(Error::TypeError)
        }
    }
}

pub struct ConfirmBlob {
    pub description: StrBuffer,
    pub extra: StrBuffer,
    pub data: StrOrBytes,
    pub description_font: &'static TextStyle,
    pub extra_font: &'static TextStyle,
    pub data_font: &'static TextStyle,
}

impl ParagraphSource for ConfirmBlob {
    fn at<'a>(&'a self, index: usize, offset: usize, buffer: &'a mut [u8]) -> Paragraph<&'a str> {
        match index {
            0 => Paragraph::new(self.description_font, &self.description.as_ref()[offset..]),
            1 => Paragraph::new(self.extra_font, &self.extra.as_ref()[offset..]),
            2 => Paragraph::new(self.data_font, self.data.as_str_offset(offset, buffer)),
            _ => unreachable!(),
        }
    }

    fn size(&self) -> usize {
        3
    }
}

pub struct PropsList {
    items: Gc<List>,
    key_font: &'static TextStyle,
    value_font: &'static TextStyle,
    value_mono_font: &'static TextStyle,
}

impl PropsList {
    pub fn new(
        obj: Obj,
        key_font: &'static TextStyle,
        value_font: &'static TextStyle,
        value_mono_font: &'static TextStyle,
    ) -> Result<Self, Error> {
        Ok(Self {
            items: obj.try_into()?,
            key_font,
            value_font,
            value_mono_font,
        })
    }
}

impl ParagraphSource for PropsList {
    fn at<'a>(&'a self, index: usize, offset: usize, buffer: &'a mut [u8]) -> Paragraph<&'a str> {
        let block = move |buffer| {
            let entry = self.items.get(index / 2)?;
            let [key, value, value_is_mono]: [Obj; 3] = iter_into_objs(entry)?;
            let value_is_mono: bool = bool::try_from(value_is_mono)?;
            let obj: Obj;
            let style: &TextStyle;

            if index % 2 == 0 {
                if !key.is_str() && key != Obj::const_none() {
                    return Err(Error::TypeError);
                }
                style = self.key_font;
                obj = key;
            } else {
                if value_is_mono {
                    style = self.value_mono_font;
                } else {
                    if value.is_bytes() {
                        return Err(Error::TypeError);
                    }
                    style = self.value_font;
                }
                obj = value;
            };

            if obj == Obj::const_none() {
                return Ok(Paragraph::new(style, ""));
            }

            let para = if obj.is_str() {
                // SAFETY:
                // As long as self is visible to GC, the string will be also. The paragraph
                // rendering does not keep the returned references for long so we can reasonably
                // expect for the chain of references from self to the buffer not to be broken.
                let s = unsafe { get_str_owner(self, obj)? };
                Paragraph::new(style, &s[offset..])
            } else if obj.is_bytes() {
                let s = StrOrBytes::hexlify(obj, offset, buffer);
                Paragraph::new(style, s)
            } else {
                return Err(Error::TypeError);
            };

            if obj == key && value != Obj::const_none() {
                Ok(para.no_break())
            } else {
                Ok(para)
            }
        };
        match block(buffer) {
            Ok(p) => p,
            Err(_) => Paragraph::new(self.value_font, "ERROR"),
        }
    }

    fn size(&self) -> usize {
        2 * self.items.len()
    }
}
