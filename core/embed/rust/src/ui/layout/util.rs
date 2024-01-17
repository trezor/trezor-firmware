use crate::{
    error::Error,
    micropython::{
        buffer::{hexlify_bytes, StrBuffer},
        gc::Gc,
        list::List,
        obj::Obj,
        util::{iter_into_array, try_or_raise},
    },
    storage::{get_avatar_len, load_avatar},
    strutil::SkipPrefix,
    ui::{
        component::text::{
            paragraphs::{Paragraph, ParagraphSource},
            TextStyle,
        },
        util::set_animation_disabled,
    },
};

/// Maximum number of characters that can be displayed on screen at once. Used
/// for on-the-fly conversion of binary data to hexadecimal representation.
/// NOTE: can be fine-tuned for particular model screen to decrease memory
/// consumption and conversion time.
pub const MAX_HEX_CHARS_ON_SCREEN: usize = 256;

pub enum StrOrBytes {
    Str(StrBuffer),
    Bytes(Obj),
}

impl StrOrBytes {
    pub fn as_str_offset(&self, offset: usize) -> StrBuffer {
        match self {
            StrOrBytes::Str(x) => x.skip_prefix(offset),
            StrOrBytes::Bytes(x) => hexlify_bytes(*x, offset, MAX_HEX_CHARS_ON_SCREEN)
                .unwrap_or_else(|_| StrBuffer::from("ERROR")),
        }
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
    type StrType = StrBuffer;

    fn at(&self, index: usize, offset: usize) -> Paragraph<Self::StrType> {
        match index {
            0 => Paragraph::new(self.description_font, self.description.skip_prefix(offset)),
            1 => Paragraph::new(self.extra_font, self.extra.skip_prefix(offset)),
            2 => Paragraph::new(self.data_font, self.data.as_str_offset(offset)),
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
    type StrType = StrBuffer;

    fn at(&self, index: usize, offset: usize) -> Paragraph<Self::StrType> {
        let block = move || {
            let entry = self.items.get(index / 2)?;
            let [key, value, value_is_mono]: [Obj; 3] = iter_into_array(entry)?;
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
                return Ok(Paragraph::new(style, StrBuffer::empty()));
            }

            let para = if obj.is_str() {
                let content: StrBuffer = obj.try_into()?;
                Paragraph::new(style, content.skip_prefix(offset))
            } else if obj.is_bytes() {
                let content = hexlify_bytes(obj, offset, MAX_HEX_CHARS_ON_SCREEN)?;
                Paragraph::new(style, content)
            } else {
                return Err(Error::TypeError);
            };

            if obj == key && value != Obj::const_none() {
                Ok(para.no_break())
            } else {
                Ok(para)
            }
        };
        match block() {
            Ok(para) => para,
            Err(_) => Paragraph::new(self.value_font, StrBuffer::from("ERROR")),
        }
    }

    fn size(&self) -> usize {
        2 * self.items.len()
    }
}

pub extern "C" fn upy_disable_animation(disable: Obj) -> Obj {
    let block = || {
        set_animation_disabled(disable.try_into()?);
        Ok(Obj::const_none())
    };
    unsafe { try_or_raise(block) }
}

pub fn get_user_custom_image() -> Result<Gc<[u8]>, Error> {
    let len = get_avatar_len()?;
    let mut data = Gc::<[u8]>::new_slice(len)?;
    // SAFETY: buffer is freshly allocated so nobody else has it.
    load_avatar(unsafe { Gc::<[u8]>::as_mut(&mut data) })?;
    Ok(data)
}
