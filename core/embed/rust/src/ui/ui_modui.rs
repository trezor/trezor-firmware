//! The screens of `modui`, the UI an app asks for, drawn per model.
//!
//! Core's `trezor.ui.modui` sequences a request into pages and menus, and each
//! screen is one [`ModUI`] call carrying the facts as the request names them.
//! Each model draws them with its own components and styles: the driver never
//! picks a screen, a font or a button.

use trezor_app_sdk::structs::{FieldKind, MAX_MENU_ENTRIES};

use crate::micropython::buffer::StrBuffer;
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

/// How many bytes of a `TextSource` field the screens take per page; the
/// driver pulls the text by it. About three screens of text, so the person
/// confirms once per chunk. The hex screen size is only a rough yardstick
/// here: how much text fits a screen depends on the text and the model.
pub const TEXT_CHUNK_BYTES: usize = 3 * MAX_HEX_CHARS_ON_SCREEN;

/// The screens of `modui`, one method per kind of screen.
///
/// `fields` always holds the facts of one page: the driver pulls a
/// `TextSource` field's text chunk by chunk and passes each page with its chunk
/// in place.
/// Every page is drawn the same way, whatever it holds: the facts in the
/// order given, each label above its value, paged by the screen when they do
/// not fit.
pub trait ModUI {
    /// One page of a review: the facts, the confirm button's label (`None`
    /// for the model's own), whether confirming is a hold, and whether a menu
    /// button opens the menu the driver runs. The menu holds a way out, so a
    /// model may leave its own off the screen; without a menu the screen
    /// offers one. How the page is drawn is the model's.
    fn review(
        title: TString<'static>,
        fields: Fields,
        verb: Option<TString<'static>>,
        hold: bool,
        menu: bool,
    ) -> Result<Gc<LayoutObj>, Error>;

    /// One page of an extra, opened from a review's menu: read-only, left
    /// without a decision, with a way to the next page.
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
            FieldKind::TextSource => self.text,
            FieldKind::Note => self.note,
            FieldKind::Warning => self.warning,
        }
    }
}

/// The facts of one page, as the driver passes them: a list of `(kind,
/// label, value)`.
///
/// `kind` is a [`FieldKind`] discriminant, read back with `FieldKind::try_from`
/// so it cannot drift from the wire's; `label` is `str`, or `None` for notes
/// and warnings; `value` is `str`, a `TextSource` field's chunk included.
/// [`Fields::new`] checks every fact, so the screens can trust them.
#[derive(Clone, Copy)]
pub struct Fields {
    items: Gc<List>,
}

impl Fields {
    /// Reads the list, refusing up front what the screens cannot draw: an
    /// unknown kind, a label where the kind has none or none where it has one,
    /// and a value of the wrong type. A page that got this far draws every
    /// fact as given.
    pub fn new(obj: Obj) -> Result<Self, Error> {
        let fields = Self {
            items: obj.try_into()?,
        };
        for index in 0..fields.items.len() {
            let (kind, label, value) = fields.get(index)?;
            let labelled = !matches!(kind, FieldKind::Note | FieldKind::Warning);
            let label_ok = if labelled {
                label.is_str()
            } else {
                label == Obj::const_none()
            };
            if !label_ok || !value.is_str() {
                return Err(Error::ValueError(c"malformed field"));
            }
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

    /// The facts as a list of paragraphs: each label above its value, each
    /// value in its kind's style.
    pub fn paragraphs(self, styles: &'static FieldStyles) -> FieldList {
        FieldList {
            fields: self,
            styles,
        }
    }

    /// Whether one of the facts is a streamed field's chunk, such as a
    /// `TextSource`'s, whose pages the model may count.
    pub fn is_streamed(&self) -> bool {
        (0..self.items.len())
            .any(|index| matches!(self.get(index), Ok((FieldKind::TextSource, _, _))))
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
            let content: StrBuffer = obj.try_into()?;
            let para = Paragraph::new(style, content.skip_prefix(offset));
            Ok::<_, Error>(if is_label {
                para.with_bottom_padding(self.styles.label_spacing)
                    .no_break()
            } else if index != self.size() - 1 {
                para.with_bottom_padding(self.styles.field_spacing)
            } else {
                para
            })
        };
        // `Fields::new` checked every fact, so this only guards against a bug.
        block().unwrap_or_else(|_| Paragraph::new(self.styles.text, StrBuffer::from("ERROR")))
    }

    fn size(&self) -> usize {
        2 * self.fields.items.len()
    }
}
