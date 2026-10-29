use crate::io::BinaryData;
use crate::micropython::buffer::{hexlify_bytes, StrBuffer};
use crate::micropython::gc::Gc;
use crate::micropython::list::List;
use crate::micropython::util::{iter_into_array, try_or_raise};
use crate::micropython::{Error, Obj};
use crate::storage::{get_avatar_len, load_avatar};
use crate::strutil::TString;
use crate::ui::component::text::paragraphs::{Paragraph, ParagraphSource};
use crate::ui::component::text::TextStyle;
use crate::ui::util::set_animation_disabled;

cfg_if::cfg_if! {
    if #[cfg(feature = "layout_bolt")] {
        use crate::ui::layout_bolt::theme;
    } else if #[cfg(feature = "layout_caesar")] {
        use crate::ui::layout_caesar::theme;
    } else if #[cfg(feature = "layout_delizia")] {
        use crate::ui::layout_delizia::theme;
    } else if #[cfg(feature = "layout_eckhart")] {
        use crate::ui::layout_eckhart::theme;
    } else {
        compile_error!("Non supported layout feature enabled");
    }
}

use theme::{
    PROPS_KEY_FONT, PROPS_SPACING, PROPS_VALUE_FONT, PROPS_VALUE_MONO_FONT, PROP_INNER_SPACING,
};

/// Maximum number of characters that can be displayed on screen at once. Used
/// for on-the-fly conversion of binary data to hexadecimal representation.
/// NOTE: can be fine-tuned for particular model screen to decrease memory
/// consumption and conversion time.
pub const MAX_HEX_CHARS_ON_SCREEN: usize = 256;

#[derive(Clone)]
pub enum StrOrBytes {
    Str(TString<'static>),
    Bytes(Obj),
}

impl StrOrBytes {
    pub fn as_str_offset(&self, offset: usize) -> TString<'static> {
        match self {
            StrOrBytes::Str(x) => x.skip_prefix(offset),
            StrOrBytes::Bytes(x) => hexlify_bytes(*x, offset, MAX_HEX_CHARS_ON_SCREEN)
                .unwrap_or_else(|_| StrBuffer::from("ERROR"))
                .into(),
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

impl From<TString<'static>> for StrOrBytes {
    fn from(value: TString<'static>) -> Self {
        StrOrBytes::Str(value)
    }
}

#[derive(Clone)]
pub struct ConfirmValueParams {
    pub description: TString<'static>,
    pub extra: TString<'static>,
    pub value: StrOrBytes,
    pub font: &'static TextStyle,
    pub description_font: &'static TextStyle,
    pub extra_font: &'static TextStyle,
}

impl ParagraphSource<'static> for ConfirmValueParams {
    fn at(&self, index: usize, offset: usize) -> Paragraph<'static> {
        match index {
            0 => Paragraph::new(self.description_font, self.description.skip_prefix(offset)),
            1 => Paragraph::new(self.extra_font, self.extra.skip_prefix(offset)),
            2 => Paragraph::new(self.font, self.value.as_str_offset(offset)),
            _ => unreachable!(),
        }
    }

    fn size(&self) -> usize {
        3
    }
}

/// How a value in a property list is drawn.
///
/// Contract C3 picks one from the third element of an item: a bool keeps
/// today's meaning (`true` = mono, `false` = plain), an int is a `FieldKind`
/// 0–5. The bool is checked first, by identity, because in Python `True == 1`,
/// which is `FieldKind::Amount`.
#[derive(Copy, Clone, PartialEq, Eq)]
pub enum PropKind {
    Plain,
    Mono,
    Text,
    Amount,
    Address,
    Data,
    Note,
    Warning,
}

impl PropKind {
    fn from_field_kind(kind: i32) -> Result<Self, Error> {
        Ok(match kind {
            0 => Self::Text,
            1 => Self::Amount,
            2 => Self::Address,
            3 => Self::Data,
            4 => Self::Note,
            5 => Self::Warning,
            _ => return Err(Error::TypeError),
        })
    }
}

/// A model's styles for the field kinds of contract C3.
///
/// P4 and P5 fill this in for Eckhart and Delizia. Until then
/// [`PropsList::new`] leaves it unset, which draws every kind in the plain
/// value font, except mono, address and data in the mono one.
#[derive(Copy, Clone)]
pub struct FieldStyles {
    pub text: &'static TextStyle,
    pub amount: &'static TextStyle,
    pub address: &'static TextStyle,
    pub data: &'static TextStyle,
    pub note: &'static TextStyle,
    pub warning: &'static TextStyle,
}

impl FieldStyles {
    /// A model that has not chosen styles: every kind is plain text.
    pub const fn plain(text: &'static TextStyle) -> Self {
        Self {
            text,
            amount: text,
            address: text,
            data: text,
            note: text,
            warning: text,
        }
    }

    pub fn style(&self, kind: PropKind) -> &'static TextStyle {
        match kind {
            PropKind::Plain | PropKind::Text => self.text,
            PropKind::Mono | PropKind::Address => self.address,
            PropKind::Amount => self.amount,
            PropKind::Data => self.data,
            PropKind::Note => self.note,
            PropKind::Warning => self.warning,
        }
    }
}

/// Reads the third element of a contract C3 item.
///
/// The bools and `None` are checked first, by identity, because in Python
/// `True == 1`, which is [`FieldKind::Amount`]; core's own layouts pass `None`
/// for "no special styling". Only then is the element read as an int kind.
fn prop_kind(kind: Obj) -> Result<PropKind, Error> {
    if kind == Obj::const_true() {
        return Ok(PropKind::Mono);
    }
    if kind == Obj::const_false() || kind == Obj::const_none() {
        return Ok(PropKind::Plain);
    }
    PropKind::from_field_kind(i32::try_from(kind)?)
}

pub struct PropsList {
    items: Gc<List>,
    key_font: &'static TextStyle,
    value_font: &'static TextStyle,
    value_mono_font: &'static TextStyle,
    key_value_padding: i16,
    props_padding: i16,
    /// A model's styles for contract C3's field kinds; `None` until P4 and P5
    /// fill theirs in.
    field_styles: Option<FieldStyles>,
}

impl PropsList {
    pub fn new_styled(
        obj: Obj,
        key_font: &'static TextStyle,
        value_font: &'static TextStyle,
        value_mono_font: &'static TextStyle,
        key_value_padding: i16,
        props_padding: i16,
    ) -> Result<Self, Error> {
        Ok(Self {
            items: obj.try_into()?,
            key_font,
            value_font,
            value_mono_font,
            key_value_padding,
            props_padding,
            field_styles: None,
        })
    }

    /// Draws contract C3's int kinds with the model's own styles.
    pub fn with_field_styles(mut self, styles: FieldStyles) -> Self {
        self.field_styles = Some(styles);
        self
    }

    /// The style for a value, from the third element of its item, and whether
    /// that kind may hold raw bytes.
    fn value_style(&self, kind: Obj) -> Result<(&'static TextStyle, bool), Error> {
        let kind = prop_kind(kind)?;
        let allow_bytes = matches!(kind, PropKind::Mono | PropKind::Address | PropKind::Data);
        let style = match (kind, self.field_styles) {
            // Core's own layouts pass a bool: they keep this list's own fonts.
            (PropKind::Plain, _) => self.value_font,
            (PropKind::Mono, _) => self.value_mono_font,
            (kind, Some(styles)) => styles.style(kind),
            // Bolt and Caesar have no styles for the field kinds yet: address and
            // data keep the mono font, every other kind is plain.
            (_, None) if allow_bytes => self.value_mono_font,
            (_, None) => self.value_font,
        };
        Ok((style, allow_bytes))
    }

    pub fn new(obj: Obj) -> Result<Self, Error> {
        Self::new_styled(
            obj,
            &PROPS_KEY_FONT,
            &PROPS_VALUE_FONT,
            &PROPS_VALUE_MONO_FONT,
            PROP_INNER_SPACING,
            PROPS_SPACING,
        )
    }

    pub fn empty() -> Result<Self, Error> {
        let empty_list = List::alloc(&[])?; // Create an empty GC list
        Self::new(empty_list.into())
    }
}

impl ParagraphSource<'static> for PropsList {
    fn at(&self, index: usize, offset: usize) -> Paragraph<'static> {
        let block = move || {
            let entry = self.items.get(index / 2)?;
            let [key, value, kind]: [Obj; 3] = iter_into_array(entry)?;
            let obj: Obj;
            let style: &TextStyle;
            let allow_bytes: bool;

            if index.is_multiple_of(2) {
                if !key.is_str() && key != Obj::const_none() {
                    return Err(Error::TypeError);
                }
                style = self.key_font;
                obj = key;
                allow_bytes = false;
            } else {
                (style, allow_bytes) = self.value_style(kind)?;
                obj = value;
            };

            if obj == Obj::const_none() {
                return Ok(Paragraph::new(style, StrBuffer::empty())
                    .with_bottom_padding(0)
                    .with_top_padding(0));
            }

            let para = if obj.is_str() {
                let content: StrBuffer = obj.try_into()?;
                Paragraph::new(style, content.skip_prefix(offset))
            } else if obj.is_bytes() {
                if !allow_bytes {
                    return Err(Error::TypeError);
                }
                let content = hexlify_bytes(obj, offset, MAX_HEX_CHARS_ON_SCREEN)?;
                Paragraph::new(style, content)
            } else {
                return Err(Error::TypeError);
            };

            if obj == key && value != Obj::const_none() {
                Ok(para.with_bottom_padding(self.key_value_padding).no_break())
            } else if (obj == key && value == Obj::const_none() && index != self.size() - 2)
                || (obj == value && index != self.size() - 1)
            {
                Ok(para.with_bottom_padding(self.props_padding))
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

/// RecoveryType as defined in `common/protob/messages-management.proto`,
/// used as arguments coming from micropython into rust world for layouts or
/// flows.
pub enum RecoveryType {
    Normal = 0,
    DryRun = 1,
    UnlockRepeatedBackup = 2,
}

// Converting `Obj` into `RecoveryType` enum
#[cfg(feature = "micropython")]
impl TryFrom<Obj> for RecoveryType {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let val = u32::try_from(obj)?;
        let this = Self::try_from(val)?;
        Ok(this)
    }
}

// Converting `u32` to `RecoveryType`
impl TryFrom<u32> for RecoveryType {
    type Error = Error;

    fn try_from(value: u32) -> Result<Self, Self::Error> {
        match value {
            0 => Ok(RecoveryType::Normal),
            1 => Ok(RecoveryType::DryRun),
            2 => Ok(RecoveryType::UnlockRepeatedBackup),
            _ => Err(Error::ValueError(c"Invalid RecoveryType")),
        }
    }
}

pub extern "C" fn upy_disable_animation(disable: Obj) -> Obj {
    let block = || {
        set_animation_disabled(disable.try_into()?);
        Ok(Obj::const_none())
    };
    unsafe { try_or_raise(block) }
}

pub fn get_user_custom_image() -> Result<BinaryData<'static>, Error> {
    let len = get_avatar_len()?;
    let mut data = Gc::<[u8]>::new_slice(len)?;
    // SAFETY: buffer is freshly allocated so nobody else has it.
    load_avatar(unsafe { Gc::<[u8]>::as_mut(&mut data) })?;
    Ok(data.into())
}

/// ContentType is used to define the type of content that can be displayed
/// in a layout or flow. It can either be an address or a public key.
pub enum ContentType {
    Address(TString<'static>),
    PublicKey(TString<'static>),
}

/// Maximum number of extended public keys (xpubs) that can be displayed in
/// a layout or flow.
pub const MAX_XPUBS: usize = 16;

#[cfg(test)]
mod tests {
    use super::*;

    /// Contract C3: `true` is mono, `false` and `None` are plain, and the bools
    /// are read before the ints. Core's own layouts pass `None`, so reading it
    /// as an int would break them.
    #[test]
    fn bool_and_none_kinds_are_read_before_ints() {
        assert!(matches!(prop_kind(Obj::const_true()), Ok(PropKind::Mono)));
        assert!(matches!(prop_kind(Obj::const_false()), Ok(PropKind::Plain)));
        assert!(matches!(prop_kind(Obj::const_none()), Ok(PropKind::Plain)));
    }
}
