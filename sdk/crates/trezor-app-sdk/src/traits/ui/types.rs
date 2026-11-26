//! The UI request types: what an app sends to core's UI and progress
//! services, and core's replies.
//!
//! Each type is serialized with [`rkyv`] and sent over IPC between the app and
//! the core task. A UI request is what `modui` builds and sends as it is: its
//! `Field` and `Extra` wrap [`WireField`] and [`WireExtra`]. Fields are `pub`
//! because core reads them straight off the archived form.
//!
//! The types also cross the [`UiV1`](super::UiV1) vtable by value, between an
//! app and a firmware that are built apart, so their layout is the app ABI.
//! That is why the enums number their variants explicitly, and why
//! [`TrezorUiEnumV1`] and [`WireField`] keep a `Reserved` variant: a new
//! variant that fits the reserved room goes at the end with a new value, and
//! no value is ever renumbered or reused. A change that does not fit is a new
//! version, such as `TrezorUiEnumV2` with its own `ui_call_v2`.

use num_enum::TryFromPrimitive;
use rkyv::{Archive, Deserialize, Serialize};
use stabby::slice::SliceMut;
use ufmt::derive::uDebug;

use crate::structs::{OptStrSlice, Slice, StrSlice};
use crate::traits::util::FastResult;

/// What a fact *is*, which decides how core formats and draws it.
///
/// The app chooses the kind by what the value is, never by how it should look.
/// Each kind has the discriminant of its [`WireField`] variant, which core reads
/// to tell the facts apart. A new kind goes at the end with a new value, and no
/// value is ever renumbered or reused.
#[stabby::stabby]
#[repr(u8)]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, TryFromPrimitive)]
pub enum FieldKind {
    /// Words or a number, shown as written.
    Text = 0,
    /// A sum formatted by the app, with its ticker kept apart.
    Amount = 1,
    /// Something compared character by character: grouped and fixed-width.
    Address = 2,
    /// Text the app hands out while core pages it. At most one per review.
    TextSource = 3,
    /// A sentence with no label: a question or an explanation.
    Note = 4,
    /// A sentence to weigh before confirming; a caution row.
    Warning = 5,
}

/// Where a [`WireField::TextSource`] field's text comes from: the app's own
/// code, which core calls back while the person pages.
///
/// Apps implement [`TextSource`](crate::modui::TextSource); `modui` wraps it in
/// this ABI-stable form.
#[stabby::stabby]
pub trait Source {
    /// Fills all of `buf` with the UTF-8 bytes starting at `offset`; an `Err`
    /// when the app's source failed.
    extern "C" fn read<'a>(&self, offset: u32, buf: SliceMut<'a, u8>) -> FastResult<(), ()>;
}

/// A borrowed [`Source`], as a request carries it.
///
/// Not serialized: it points into the app's own memory, which does not cross
/// IPC.
#[stabby::stabby]
#[derive(Copy, Clone)]
pub struct SourceRef<'a> {
    inner: stabby::dynptr!(&'a dyn Source),
}

impl<'a> SourceRef<'a> {
    pub(crate) fn new(inner: stabby::dynptr!(&'a dyn Source)) -> Self {
        Self { inner }
    }

    /// Fills `buf` with the bytes at `offset`; `false` when the app's source
    /// failed.
    pub fn read(&self, offset: u32, buf: &mut [u8]) -> bool {
        self.inner.read(offset, buf.into()).into_result().is_ok()
    }
}

// A source has nothing to print.
impl ufmt::uDebug for SourceRef<'_> {
    fn fmt<W: ?Sized>(&self, f: &mut ufmt::Formatter<'_, W>) -> Result<(), W::Error>
    where
        W: ufmt::uWrite,
    {
        f.write_str("<source>")
    }
}

/// One fact in a [`ReviewRequest`] or one of its extras. Each kind carries only
/// what it needs; its discriminant is its [`FieldKind`].
///
/// A `TextSource` crosses IPC as its label and length: core pulls the text
/// itself from `source` in chunks while the person pages.
#[stabby::stabby]
#[repr(C, u8)]
#[derive(uDebug, Copy, Clone, Archive, Serialize)]
pub enum WireField<'a> {
    /// See [`FieldKind::Text`].
    Text {
        /// The name above the value.
        label: StrSlice<'a>,
        /// The value.
        value: StrSlice<'a>,
    } = 0,
    /// See [`FieldKind::Amount`].
    Amount {
        /// The name above the value.
        label: StrSlice<'a>,
        /// The number, as the person should read it.
        value: StrSlice<'a>,
        /// The unit, such as `"TRX"`.
        ticker: StrSlice<'a>,
    } = 1,
    /// See [`FieldKind::Address`].
    Address {
        /// The name above the value.
        label: StrSlice<'a>,
        /// The value.
        value: StrSlice<'a>,
    } = 2,
    /// See [`FieldKind::TextSource`].
    TextSource {
        /// The name above the value.
        label: StrSlice<'a>,
        /// The text's length in UTF-8 bytes.
        len: u32,
        /// Where the text comes from.
        #[rkyv(with = rkyv::with::Skip)]
        source: SourceRef<'a>,
    } = 3,
    /// See [`FieldKind::Note`].
    Note {
        /// The sentence.
        text: StrSlice<'a>,
    } = 4,
    /// See [`FieldKind::Warning`].
    Warning {
        /// The sentence.
        text: StrSlice<'a>,
    } = 5,
    /// Never sent. Reserves room, so that a later kind fits without changing
    /// the size of a field.
    #[doc(hidden)]
    Reserved(
        /// Unused.
        [usize; 8],
    ) = 255,
}

impl WireField<'_> {
    /// Whether core pulls this fact's text from the app while the person pages.
    pub(crate) fn is_streamed(&self) -> bool {
        matches!(self, Self::TextSource { .. })
    }

    /// The kind of fact this is.
    pub fn kind(&self) -> Option<FieldKind> {
        Some(match self {
            Self::Text { .. } => FieldKind::Text,
            Self::Amount { .. } => FieldKind::Amount,
            Self::Address { .. } => FieldKind::Address,
            Self::TextSource { .. } => FieldKind::TextSource,
            Self::Note { .. } => FieldKind::Note,
            Self::Warning { .. } => FieldKind::Warning,
            Self::Reserved(_) => return None,
        })
    }
}

// Message ids on the UI service. A decision is the request's own id; a chunk
// request has its own so that neither is mistaken for a decision. Each chunk
// request is answered with the chunk itself, or with the chunk-failed id when
// the app cannot produce it, so the two alternate until core sends the
// decision.

/// The id of a request, and of core's decision on it.
pub const UI_MSG_DECISION: u16 = 0;
/// The id of core's [`UiChunkRequest`], and of the app's chunk that answers it.
pub const UI_MSG_CHUNK: u16 = 1;
/// The id of the app's answer when its source could not produce a chunk.
pub const UI_MSG_CHUNK_FAILED: u16 = 2;

/// One chunk of a `TextSource` field, as core asks the app for it.
///
/// `field` is the field's flat index: the request's own facts first, then each
/// extra's facts in order. The app answers with the bytes themselves.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub struct UiChunkRequest {
    /// The field's flat index.
    pub field: u16,
    /// Where the chunk starts.
    pub offset: u32,
    /// How many bytes to read.
    pub len: u32,
}

/// More the person can open from a review's menu: the entry's label, and the
/// facts shown when it is picked.
#[stabby::stabby]
#[derive(uDebug, Copy, Clone, Archive, Serialize)]
pub struct WireExtra<'a> {
    /// The menu entry's label.
    pub label: StrSlice<'a>,
    /// The facts shown when the entry is picked.
    pub fields: Slice<'a, WireField<'a>>,
}

/// How many entries a request's menu may hold, on every model.
///
/// Every entry counts: each offered extra takes one, the way out (Cancel) takes
/// one, and a details answer's "Show all" takes one more. So a review offers
/// at most five extras, details at most four, and a danger none, because its
/// menu already holds the way forward. See [`Answer::max_extras`].
pub const MAX_MENU_ENTRIES: usize = 6;

/// How many streamed fields, such as a `TextSource`, one list of facts may
/// hold: a review's own facts, or one extra's.
pub const MAX_STREAMED_FIELDS: usize = 1;

/// How the person answers a review, which decides how core draws its yes.
#[stabby::stabby]
#[repr(u8)]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, TryFromPrimitive)]
pub enum Answer {
    /// A step: a tap, with the menu for the extras and the way out.
    Confirm = 0,
    /// The strong yes: a deliberate confirmation, usable mid-flow, drawn as a
    /// hold where the model has one.
    Strong = 1,
    /// Going on is risky: refusing is the default.
    Danger = 2,
    /// The short version, with "Show all" in the menu. Answered with
    /// [`TrezorUiResultV1::ShowDetails`] or [`TrezorUiResultV1::Confirmed`].
    Details = 3,
}

impl Answer {
    /// How many extras a review with this answer may offer: what is left of
    /// [`MAX_MENU_ENTRIES`] after the entries of its own.
    pub const fn max_extras(self) -> usize {
        match self {
            Self::Confirm | Self::Strong => MAX_MENU_ENTRIES - 1,
            Self::Details => MAX_MENU_ENTRIES - 2,
            Self::Danger => 0,
        }
    }
}

/// Facts for the person to read, then answer as `answer` says; sent as
/// [`TrezorUiEnumV1::Review`].
#[stabby::stabby]
#[derive(uDebug, Copy, Clone, Archive, Serialize)]
pub struct ReviewRequest<'a> {
    /// The step's name, relative to the app.
    pub step: StrSlice<'a>,
    /// The screen title.
    pub title: StrSlice<'a>,
    /// The facts to read.
    pub fields: Slice<'a, WireField<'a>>,
    /// The extras the menu offers.
    pub extras: Slice<'a, WireExtra<'a>>,
    /// How the person answers.
    pub answer: Answer,
}

/// An address or public key of the person's own, sent as
/// [`TrezorUiEnumV1::VerifyAddress`] or [`TrezorUiEnumV1::VerifyPubkey`].
#[stabby::stabby]
#[derive(uDebug, Copy, Clone, Archive, Serialize)]
pub struct VerifyRequest<'a> {
    /// The step's name, relative to the app.
    pub step: StrSlice<'a>,
    /// The address or public key.
    pub value: StrSlice<'a>,
    /// The account it belongs to.
    pub account: OptStrSlice<'a>,
    /// Its derivation path.
    pub path: OptStrSlice<'a>,
}

/// The end of a flow, sent as [`TrezorUiEnumV1::Done`].
#[stabby::stabby]
#[derive(uDebug, Copy, Clone, Archive, Serialize)]
pub struct DoneRequest<'a> {
    /// The step's name, relative to the app.
    pub step: StrSlice<'a>,
    /// What was done.
    pub text: StrSlice<'a>,
}

/// One UI request, as it crosses IPC: one variant per decision an app asks.
///
/// The discriminants match the wire's: a new variant goes at the end with a
/// new value, and no value is ever renumbered or reused.
#[stabby::stabby]
#[repr(C, u8)]
#[derive(uDebug, Copy, Clone, Archive, Serialize)]
pub enum TrezorUiEnumV1<'a> {
    /// Facts to read and answer.
    Review(ReviewRequest<'a>) = 0,
    /// An address of the person's own to check.
    VerifyAddress(VerifyRequest<'a>) = 1,
    /// A public key of the person's own to check.
    VerifyPubkey(VerifyRequest<'a>) = 2,
    /// The end of a flow.
    Done(DoneRequest<'a>) = 3,
    /// Never sent. Reserves room, so that a later request fits without
    /// changing the size of this type.
    #[doc(hidden)]
    Reserved(
        /// Unused.
        [usize; 16],
    ) = 255,
}

// The discriminants by name, for core to tell the requests apart. The ABI test
// (`abi.rs`) checks them against the enum's own tags.
impl TrezorUiEnumV1<'_> {
    /// The discriminant of [`TrezorUiEnumV1::Review`].
    pub const REVIEW: u16 = 0;
    /// The discriminant of [`TrezorUiEnumV1::VerifyAddress`].
    pub const VERIFY_ADDRESS: u16 = 1;
    /// The discriminant of [`TrezorUiEnumV1::VerifyPubkey`].
    pub const VERIFY_PUBKEY: u16 = 2;
    /// The discriminant of [`TrezorUiEnumV1::Done`].
    pub const DONE: u16 = 3;
}

/// How the person decided a request. Written by core, read by `modui`; apps
/// never see it.
///
/// Variants say what the person *did*, not which button did it. Only the
/// request's final answer crosses: what happens in its menu stays in core.
#[must_use]
#[stabby::stabby]
#[repr(u8)]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize, TryFromPrimitive)]
pub enum TrezorUiResultV1 {
    /// Confirmed.
    Confirmed = 0,
    /// Refused, or left without answering.
    Cancelled = 1,
    /// The person asked to see details.
    ShowDetails = 2,
}

/// Progress bar operations that can be requested from the app via IPC.
///
/// Built by `core/embed/api`; apps use `modui::progress`.
///
/// `Init` opens the progress, `Step` reports work done, `Label` changes the
/// text under the bar, and `End` closes it. Core keeps the count and turns it
/// into the bar. The app SDK pairs them with a guard that sends `End` on drop,
/// so an app cannot leave a progress on screen for work that stopped; see the
/// `modui` progress docs.
///
/// Only what the app chose travels; how the progress looks is core's.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, Archive, Serialize, Deserialize)]
pub enum TrezorProgressEnum<'a> {
    /// Show a progress indicator.
    Init {
        /// What the work is, such as `"Signing"`.
        label: StrSlice<'a>,
        /// How much work there is, in the app's own units. `0` means not
        /// known: the bar shows motion rather than a fill.
        total: u32,
    },
    /// Reports more of the work done.
    Step {
        /// Units of work done since the last step.
        units: u32,
    },
    /// Changes the text under the bar while the work goes on.
    Label {
        /// What the work is now, such as `"Signing input 2/3"`.
        label: StrSlice<'a>,
    },
    /// Close the progress indicator.
    End,
}

impl<'a> TrezorProgressEnum<'a> {
    /// The message id of [`TrezorProgressEnum::Init`].
    pub const INIT: u16 = 0;
    /// The message id of [`TrezorProgressEnum::Step`].
    pub const STEP: u16 = 1;
    /// The message id of [`TrezorProgressEnum::Label`].
    pub const LABEL: u16 = 2;
    /// The message id of [`TrezorProgressEnum::End`].
    pub const END: u16 = 3;

    /// The message id of the request.
    pub fn id(&self) -> u16 {
        match self {
            TrezorProgressEnum::Init { .. } => Self::INIT,
            TrezorProgressEnum::Step { .. } => Self::STEP,
            TrezorProgressEnum::Label { .. } => Self::LABEL,
            TrezorProgressEnum::End => Self::END,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Ensures every variant of TrezorProgressEnum has a unique id()
    /// and that no variant is accidentally forgotten.
    #[test]
    fn progress_ids_are_unique_and_exhaustive() {
        use TrezorProgressEnum::*;
        let variants: &[(u16, &str)] = &[
            (
                Init {
                    label: "".into(),
                    total: 0,
                }
                .id(),
                "Init",
            ),
            (Step { units: 0 }.id(), "Step"),
            (Label { label: "".into() }.id(), "Label"),
            (End.id(), "End"),
        ];
        // all IDs must be unique
        let mut seen = std::collections::HashSet::new();
        for (id, name) in variants {
            assert!(seen.insert(id), "duplicate id {} for variant {}", id, name);
        }
        // total count must match — add new variants here when extending the enum
        assert_eq!(variants.len(), 4, "new variant added but test not updated");
    }

    #[test]
    fn the_menu_budget_leaves_room_for_each_answer() {
        assert_eq!(Answer::Confirm.max_extras(), 5);
        assert_eq!(Answer::Strong.max_extras(), 5);
        assert_eq!(Answer::Details.max_extras(), 4);
        assert_eq!(Answer::Danger.max_extras(), 0);
    }

    #[test]
    fn a_chunk_request_round_trips() {
        let request = UiChunkRequest {
            field: 7,
            offset: 384,
            len: 384,
        };
        let bytes = rkyv::to_bytes::<rkyv::rancor::Error>(&request).unwrap();
        let archived =
            rkyv::access::<rkyv::Archived<UiChunkRequest>, rkyv::rancor::Failure>(&bytes).unwrap();
        assert_eq!(archived.field, 7);
        assert_eq!(archived.offset, 384);
        assert_eq!(archived.len, 384);
    }
}
