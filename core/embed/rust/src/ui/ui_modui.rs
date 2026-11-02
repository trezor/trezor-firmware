//! The screens of `modui`, the UI an app asks for, drawn per model.
//!
//! Core's `trezor.ui.modui` sequences a request into pages and menus, and each
//! screen is one [`ModUI`] call carrying the facts as the request names them.
//! Each model draws them with its own components and styles: the driver never
//! picks a screen, a font or a button.

use trezor_app_sdk::structs::{FieldKind, MAX_MENU_ENTRIES};

use crate::micropython::buffer::{hexlify_bytes, StrBuffer};
use crate::micropython::gc::Gc;
use crate::micropython::list::List;
use crate::micropython::util::iter_into_array;
use crate::micropython::{Error, Obj};
use crate::strutil::TString;
use crate::ui::component::text::paragraphs::{Paragraph, ParagraphSource};
use crate::ui::component::text::TextStyle;
use crate::ui::layout::obj::LayoutObj;
use crate::ui::layout::util::MAX_HEX_CHARS_ON_SCREEN;
use crate::ui::ui_firmware::MAX_MENU_ITEMS;

// Every entry a request's menu may hold must fit the menu the models draw.
const _: () = assert!(MAX_MENU_ENTRIES <= MAX_MENU_ITEMS);

/// The screens of `modui`, one method per kind of screen.
///
/// `fields` always holds the facts of one page: the driver pulls a `Data`
/// field's bytes chunk by chunk and passes each page with its chunk in place.
pub trait ModUI {
    /// One page of a review: the facts, the confirm button's label (`None`
    /// for the model's own), whether confirming is a hold, and whether a menu
    /// button opens the menu the driver runs. With a menu the way out lives in
    /// it; without one the screen offers its own.
    fn review(
        title: TString<'static>,
        fields: Fields,
        verb: Option<TString<'static>>,
        hold: bool,
        menu: bool,
    ) -> Result<Gc<LayoutObj>, Error>;

    /// One page of an extra, opened from a review's menu: read-only, left
    /// without a decision.
    fn extra(title: TString<'static>, fields: Fields) -> Result<Gc<LayoutObj>, Error>;

    /// One page of a danger: refusing is the default, and going on is a
    /// deliberate detour.
    fn danger(title: TString<'static>, fields: Fields) -> Result<Gc<LayoutObj>, Error>;

    /// The person's own address to check against the host. `br_name` names
    /// the screen's ButtonRequest.
    fn verify_address(
        address: TString<'static>,
        account: Option<TString<'static>>,
        path: Option<TString<'static>>,
        br_name: TString<'static>,
    ) -> Result<Gc<LayoutObj>, Error>;

    /// The person's own public key to check against the host. `br_name` names
    /// the screen's ButtonRequest.
    fn verify_pubkey(
        pubkey: TString<'static>,
        account: Option<TString<'static>>,
        path: Option<TString<'static>>,
        br_name: TString<'static>,
    ) -> Result<Gc<LayoutObj>, Error>;

    /// The flow is finished, and `text` says how. Goes away after `time_ms`,
    /// or on a tap when it is 0.
    fn done(text: TString<'static>, time_ms: u32) -> Result<Gc<LayoutObj>, Error>;
}

/// A model's styles for the field kinds, and the spacing of a list of facts.
pub struct FieldStyles {
    pub label: &'static TextStyle,
    pub text: &'static TextStyle,
    pub amount: &'static TextStyle,
    pub address: &'static TextStyle,
    pub data: &'static TextStyle,
    pub note: &'static TextStyle,
    pub warning: &'static TextStyle,
    /// Between a label and its value.
    pub label_spacing: i16,
    /// Between one fact and the next.
    pub field_spacing: i16,
}

impl FieldStyles {
    fn value(&self, kind: FieldKind) -> &'static TextStyle {
        match kind {
            FieldKind::Text => self.text,
            FieldKind::Amount => self.amount,
            FieldKind::Address => self.address,
            FieldKind::Data => self.data,
            FieldKind::Note => self.note,
            FieldKind::Warning => self.warning,
        }
    }
}

/// The facts of one page, as the driver passes them: a list of `(kind,
/// label, value)`.
///
/// `kind` is a [`FieldKind`] discriminant, read back with `FieldKind::try_from`
/// so it cannot drift from the wire's; `label` is `None` for notes and
/// warnings; `value` is `str`, or `bytes` for a `Data` field's chunk.
#[derive(Clone, Copy)]
pub struct Fields {
    items: Gc<List>,
}

/// What a page holds, which decides the screen it is drawn on.
pub enum Shape {
    /// Only notes, joined one per line.
    Sentences(TString<'static>),
    /// One value, with the page's notes as its description.
    Value {
        kind: FieldKind,
        value: Obj,
        description: Option<TString<'static>>,
    },
    /// Several values, or any warning: a list of facts, where a warning is a
    /// caution row.
    List,
}

impl Fields {
    /// Reads the list, refusing an unknown kind up front.
    pub fn new(obj: Obj) -> Result<Self, Error> {
        let fields = Self {
            items: obj.try_into()?,
        };
        for index in 0..fields.items.len() {
            fields.get(index)?;
        }
        Ok(fields)
    }

    /// The fact at `index`: its kind, its label and its value.
    fn get(&self, index: usize) -> Result<(FieldKind, Obj, Obj), Error> {
        let [kind, label, value]: [Obj; 3] = iter_into_array(self.items.get(index)?)?;
        let kind = FieldKind::try_from(u8::try_from(kind)?)
            .map_err(|_| Error::ValueError(c"unknown field kind"))?;
        Ok((kind, label, value))
    }

    fn kinds(&self) -> impl Iterator<Item = (FieldKind, Obj)> + '_ {
        (0..self.items.len()).filter_map(|index| {
            let (kind, _, value) = self.get(index).ok()?;
            Some((kind, value))
        })
    }

    /// What the page holds: notes only, one value, or a list.
    pub fn shape(&self) -> Result<Shape, Error> {
        let is_sentence = |kind| matches!(kind, FieldKind::Note | FieldKind::Warning);
        let values = self.kinds().filter(|(kind, _)| !is_sentence(*kind)).count();
        let has_warning = self.kinds().any(|(kind, _)| kind == FieldKind::Warning);
        if values > 1 || has_warning {
            return Ok(Shape::List);
        }
        let sentences = self.sentences()?;
        Ok(match self.kinds().find(|(kind, _)| !is_sentence(*kind)) {
            Some((kind, value)) => Shape::Value {
                kind,
                value,
                description: sentences,
            },
            None => Shape::Sentences(sentences.unwrap_or_else(TString::empty)),
        })
    }

    /// The page's notes, one per line, or `None` if it has none. A page with a
    /// warning is a list, so only notes get here.
    fn sentences(&self) -> Result<Option<TString<'static>>, Error> {
        let mut texts: heapless::Vec<StrBuffer, 8> = heapless::Vec::new();
        for (kind, value) in self.kinds() {
            if kind == FieldKind::Note {
                texts
                    .push(value.try_into()?)
                    .map_err(|_| Error::ValueError(c"too many sentences"))?;
            }
        }
        if texts.is_empty() {
            return Ok(None);
        }
        let len = texts.iter().map(|text| text.len() + 1).sum::<usize>() - 1;
        let joined = StrBuffer::alloc_with(len, |buf| {
            let mut at = 0;
            for (i, text) in texts.iter().enumerate() {
                if i > 0 {
                    buf[at] = b'\n';
                    at += 1;
                }
                buf[at..at + text.len()].copy_from_slice(text.as_ref().as_bytes());
                at += text.len();
            }
        })?;
        Ok(Some(joined.into()))
    }

    /// The facts as a list of paragraphs: each label above its value, each
    /// value in its kind's style.
    pub fn paragraphs(self, styles: &'static FieldStyles) -> FieldList {
        FieldList {
            fields: self,
            styles,
        }
    }
}

/// The facts of a page as paragraphs: a label and a value for each, the label
/// empty for notes and warnings.
pub struct FieldList {
    fields: Fields,
    styles: &'static FieldStyles,
}

impl ParagraphSource<'static> for FieldList {
    fn at(&self, index: usize, offset: usize) -> Paragraph<'static> {
        let block = || {
            let (kind, label, value) = self.fields.get(index / 2)?;
            let is_label = index.is_multiple_of(2);
            let (obj, style) = if is_label {
                (label, self.styles.label)
            } else {
                (value, self.styles.value(kind))
            };
            if obj == Obj::const_none() {
                return Ok(Paragraph::new(style, StrBuffer::empty())
                    .with_bottom_padding(0)
                    .with_top_padding(0));
            }
            let para = if obj.is_str() {
                let content: StrBuffer = obj.try_into()?;
                Paragraph::new(style, content.skip_prefix(offset))
            } else if obj.is_bytes() && kind == FieldKind::Data {
                Paragraph::new(style, hexlify_bytes(obj, offset, MAX_HEX_CHARS_ON_SCREEN)?)
            } else {
                return Err(Error::TypeError);
            };
            Ok(if is_label {
                para.with_bottom_padding(self.styles.label_spacing)
                    .no_break()
            } else if index != self.size() - 1 {
                para.with_bottom_padding(self.styles.field_spacing)
            } else {
                para
            })
        };
        match block() {
            Ok(para) => para,
            Err(_) => Paragraph::new(self.styles.text, StrBuffer::from("ERROR")),
        }
    }

    fn size(&self) -> usize {
        2 * self.fields.items.len()
    }
}
