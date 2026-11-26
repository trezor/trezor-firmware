//! One fact for the person to read. The public docs live on [`Field`].
//!
//! A fact is what it is, never how it looks: the constructor names the kind of
//! value, and core decides the styling, the grouping and the paging of that kind
//! on every model. Nothing here holds behaviour.

use stabby::slice::SliceMut;

use crate::modui::call::set_source_error;
use crate::structs::Slice;
use crate::traits::ui::{MAX_STREAMED_FIELDS, Source, SourceRef, WireField};
use crate::traits::util::FastResult;
use crate::{Error, Result};

/// One thing the person reads: a label and a value, or a sentence on its own.
///
/// What a fact *is* decides how it looks, on every model; the app never picks a
/// style. A list of facts can mix all six kinds, a warning included.
///
/// | Constructor | For | Example |
/// |---|---|---|
/// | [`text`](Field::text) | Words or a number, shown as written. | `Field::text("Resource", "Energy")` |
/// | [`amount`](Field::amount) | A sum, formatted by the app, and its unit. | `Field::amount("Amount", "1.5", "TRX")` |
/// | [`address`](Field::address) | Something compared character by character. | `Field::address("Recipient", &to)` |
/// | [`text_source`](Field::text_source) | Long text the app hands out while core pages it. | `Field::text_source("Message", len, &source)` |
/// | [`note`](Field::note) | A sentence with no label: a question or an explanation. | `Field::note("Allow access to your balance?")` |
/// | [`warning`](Field::warning) | A sentence to weigh before confirming. | `Field::warning("This address is not yours.")` |
///
/// # Example
///
/// ```no_run
/// use trezor_app_sdk::modui::Field;
///
/// let facts = [
///     Field::address("Recipient", "TRX..."),
///     Field::amount("Amount", "1,000", "TRX"),
///     Field::text("Resource", "Energy"),
/// ];
/// ```
#[derive(Copy, Clone)]
#[repr(transparent)]
pub struct Field<'a> {
    wire: WireField<'a>,
}

/// Where a [`text_source`](Field::text_source) field's text comes from, read
/// by core while the person pages.
///
/// Core reads in order, from offset 0, in contiguous ranges, and asks for each
/// range once, so a source may hash what it hands out. It stops when the person
/// reaches the end of the field or refuses it. The bytes are UTF-8; a range may
/// end inside a character, and core joins it with the next range.
///
/// `read` runs inside the review's own call to core, while that call still
/// waits for the person's decision, and an app has one call to core in flight
/// at a time. So `read` must not call core or the host: a wire, crypto or UI
/// call from inside it stops the app. The text comes from the app itself —
/// held, decoded or generated. Reading it from the host needs a protocol that
/// does not exist yet.
///
/// `read` takes `&self` so that a [`Field`] stays `Copy`: a source that keeps
/// state keeps it in a `Cell` or `RefCell` of its own.
pub trait TextSource {
    /// Fills all of `buf` with the UTF-8 bytes starting at `offset`.
    fn read(&self, offset: u32, buf: &mut [u8]) -> Result<()>;
}

impl<T: TextSource + ?Sized> TextSource for &T {
    fn read(&self, offset: u32, buf: &mut [u8]) -> Result<()> {
        (**self).read(offset, buf)
    }
}

// What core calls: every app source, in the ABI-stable form. The error itself
// stays in the app, kept for the answer of the call that is running.
impl<T: TextSource> Source for T {
    extern "C" fn read<'a>(&self, offset: u32, mut buf: SliceMut<'a, u8>) -> FastResult<(), ()> {
        TextSource::read(self, offset, &mut buf)
            .map_err(set_source_error)
            .into()
    }
}

impl<'a> Field<'a> {
    /// Words or a number, shown as written.
    ///
    /// Use it for anything the person reads rather than compares: a resource
    /// name, a memo, a count.
    ///
    /// # Example
    ///
    /// ```no_run
    /// use trezor_app_sdk::modui::Field;
    ///
    /// let resource = Field::text("Resource", "Energy");
    /// ```
    pub fn text(label: &'a str, value: &'a str) -> Self {
        Self::from(WireField::Text {
            label: label.into(),
            value: value.into(),
        })
    }

    /// A sum, and the ticker of what it counts: `"1.5"` and `"TRX"`.
    ///
    /// Core does not do the arithmetic or pick the unit; the app writes the
    /// number as the person should read it, sign included (`"-1,000"`), and
    /// names its ticker apart. How the two are drawn together is core's.
    ///
    /// # Example
    ///
    /// ```no_run
    /// use trezor_app_sdk::modui::Field;
    ///
    /// let amount = Field::amount("Amount", "1.5", "TRX");
    /// ```
    pub fn amount(label: &'a str, value: &'a str, ticker: &'a str) -> Self {
        Self::from(WireField::Amount {
            label: label.into(),
            value: value.into(),
            ticker: ticker.into(),
        })
    }

    /// Something compared character by character: an address, a key, a
    /// contract id.
    ///
    /// Core groups it into chunks and draws it fixed-width, so the person can
    /// compare it against the host's copy without losing their place.
    ///
    /// # Example
    ///
    /// ```no_run
    /// use trezor_app_sdk::modui::Field;
    ///
    /// let recipient = Field::address("Recipient", "TRX...");
    /// ```
    pub fn address(label: &'a str, value: &'a str) -> Self {
        Self::from(WireField::Address {
            label: label.into(),
            value: value.into(),
        })
    }

    /// Long text the app does not hand over at once, such as a message to
    /// sign. Core pages it like [`text`](Field::text) and pulls it from
    /// `source` while the person reads.
    ///
    /// At most one per list of facts. It may not sit in an extra: an extra can
    /// be opened again, and its text would be read again. That is
    /// [`Error::DataError`].
    ///
    /// Core reads the source as [`TextSource`] describes. If `read` fails, the
    /// review ends as refused and the app gets the source's own error back, not
    /// [`Error::Cancelled`](crate::Error::Cancelled).
    ///
    /// `len` is the text's length in UTF-8 bytes, the source's to know.
    ///
    /// A trait object works too: `&dyn TextSource` is itself a `TextSource`
    /// through the blanket `impl for &T`, so pass it as `&source`.
    ///
    /// # Example
    ///
    /// ```no_run
    /// use core::cell::RefCell;
    /// use core::fmt::Write as _;
    /// use trezor_app_sdk::crypto::{self as sdk, HasherExt, HashingAlgorithm};
    /// use trezor_app_sdk::modui::{self, Field, TextSource};
    /// use trezor_app_sdk::traits::crypto::BoxedHasher;
    /// use trezor_app_sdk::{Error, Result};
    ///
    /// /// A message handed out range by range, hashed on the way out.
    /// struct Message<'a> {
    ///     text: &'a str,
    ///     hasher: RefCell<BoxedHasher>,
    /// }
    ///
    /// impl TextSource for Message<'_> {
    ///     fn read(&self, offset: u32, buf: &mut [u8]) -> Result<()> {
    ///         let start = offset as usize;
    ///         let end = start + buf.len();
    ///         let bytes = self.text.as_bytes().get(start..end).ok_or(Error::DataError("out of text"))?;
    ///         buf.copy_from_slice(bytes);
    ///         self.hasher.borrow_mut().update(buf);
    ///         Ok(())
    ///     }
    /// }
    ///
    /// fn confirm_message(text: &str) -> Result<()> {
    ///     let message = Message {
    ///         text,
    ///         hasher: RefCell::new(sdk::get_hasher(HashingAlgorithm::Sha256)),
    ///     };
    ///     let field = Field::text_source("Message", text.len() as u32, &message);
    ///     modui::review("message", "Sign message", &[field]).confirm()?;
    ///
    ///     let digest = message.hasher.into_inner().finalize();
    ///     let mut hash = String::new();
    ///     for byte in digest.as_ref() {
    ///         let _ = write!(hash, "{:02x}", byte);
    ///     }
    ///     modui::review("summary", "Signed", &[Field::address("Hash", &hash)]).confirm_strong()
    /// }
    /// ```
    pub fn text_source<S: TextSource + 'a>(label: &'a str, len: u32, source: &'a S) -> Self {
        Self::from(WireField::TextSource {
            label: label.into(),
            len,
            source: SourceRef::new(source.into()),
        })
    }

    /// A sentence with no label: a question or an explanation.
    ///
    /// Core draws it as a paragraph of its own, without a key to its left.
    ///
    /// # Example
    ///
    /// ```no_run
    /// use trezor_app_sdk::modui::Field;
    ///
    /// let question = Field::note("Allow access to your balance?");
    /// ```
    pub fn note(text: &'a str) -> Self {
        Self::from(WireField::Note { text: text.into() })
    }

    /// A sentence the person should weigh before confirming, drawn as a caution
    /// row.
    ///
    /// Use it for what makes this decision risky, not for ordinary guidance: a
    /// hint is core's to show, not the app's.
    ///
    /// # Example
    ///
    /// ```no_run
    /// use trezor_app_sdk::modui::Field;
    ///
    /// let caution = Field::warning("This address is not yours.");
    /// ```
    pub fn warning(text: &'a str) -> Self {
        Self::from(WireField::Warning { text: text.into() })
    }

    fn from(wire: WireField<'a>) -> Self {
        Self { wire }
    }
}

/// Borrows a list of `#[repr(transparent)]` wrappers as the list they wrap.
///
/// # Safety
///
/// `W` must be `#[repr(transparent)]` over `T`, so a `&[W]` has the layout of
/// a `&[T]` of the same length.
pub(crate) unsafe fn unwrap_slice<W, T>(items: &[W]) -> &[T] {
    // SAFETY: see the function's contract.
    unsafe { core::slice::from_raw_parts(items.as_ptr().cast::<T>(), items.len()) }
}

/// A list of facts, as a request carries them: a borrow, not a copy.
pub(crate) fn wire_fields<'a>(fields: &'a [Field<'a>]) -> Slice<'a, WireField<'a>> {
    // SAFETY: `Field` is `#[repr(transparent)]` over `WireField`.
    Slice::new(unsafe { unwrap_slice(fields) })
}

/// Checks one list of facts before it is sent: at most
/// [`MAX_STREAMED_FIELDS`] streamed fields, such as a
/// [`text_source`](Field::text_source).
///
/// What they stream is not limited: core pulls it from the app, so the request
/// only carries its length.
pub(crate) fn check_fields(fields: &[WireField<'_>]) -> Result<()> {
    if fields.iter().filter(|field| field.is_streamed()).count() > MAX_STREAMED_FIELDS {
        return Err(Error::DataError("too many streamed fields"));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::traits::ui::FieldKind;

    /// The text a source hands out, range by range.
    struct Text(&'static str);

    impl TextSource for Text {
        fn read(&self, offset: u32, buf: &mut [u8]) -> Result<()> {
            let start = offset as usize;
            let bytes = self.0.as_bytes().get(start..start + buf.len());
            buf.copy_from_slice(bytes.ok_or(Error::DataError("out of text"))?);
            Ok(())
        }
    }

    #[test]
    fn a_note_carries_its_text_and_no_label() {
        let note = Field::note("Continue?");
        assert!(note.wire.kind() == Some(FieldKind::Note));
        assert!(matches!(note.wire, WireField::Note { text } if text.as_str() == "Continue?"));
    }

    #[test]
    fn text_facts_carry_their_label_and_value() {
        let text = Field::text("Resource", "Energy");
        assert!(text.wire.kind() == Some(FieldKind::Text));
        assert!(matches!(
            text.wire,
            WireField::Text { label, value }
                if label.as_str() == "Resource" && value.as_str() == "Energy"
        ));
    }

    #[test]
    fn an_amount_carries_its_ticker_apart() {
        let amount = Field::amount("Amount", "1.5", "TRX");
        assert!(amount.wire.kind() == Some(FieldKind::Amount));
        assert!(matches!(
            amount.wire,
            WireField::Amount { label, value, ticker }
                if label.as_str() == "Amount" && value.as_str() == "1.5" && ticker.as_str() == "TRX"
        ));
    }

    #[test]
    fn a_text_source_reads_through_the_abi() {
        let source = Text("hello");
        let field = Field::text_source("a", 5, &source);
        let WireField::TextSource { len, source, .. } = field.wire else {
            panic!("not a text source");
        };
        assert_eq!(len, 5);
        let mut buf = [0u8; 3];
        assert!(source.read(1, &mut buf));
        assert_eq!(&buf, b"ell");
        assert!(!source.read(4, &mut buf));
    }

    #[test]
    fn a_second_text_source_is_refused() {
        let (a, b) = (Text("a"), Text("b"));
        let fields = [
            Field::text_source("a", 1, &a),
            Field::text_source("b", 1, &b),
        ];
        assert!(matches!(
            check_fields(wire_fields(&fields).as_slice()),
            Err(Error::DataError("too many streamed fields"))
        ));
    }

    #[test]
    fn one_text_source_beside_text_is_accepted() {
        let source = Text("abc");
        let fields = [Field::text_source("a", 3, &source), Field::text("b", "c")];
        assert!(check_fields(wire_fields(&fields).as_slice()).is_ok());
    }

    #[test]
    fn the_request_does_not_grow_with_the_text() {
        use crate::traits::ui::{Answer, ReviewRequest, TrezorUiEnumV1};

        fn size(len: u32) -> usize {
            let source = Text("");
            let fields = [Field::text_source("a", len, &source)];
            let request = TrezorUiEnumV1::Review(ReviewRequest {
                step: "s".into(),
                title: "t".into(),
                fields: wire_fields(&fields),
                extras: Slice::new(&[]),
                answer: Answer::Confirm,
            });
            rkyv::to_bytes::<rkyv::rancor::Error>(&request)
                .unwrap()
                .len()
        }

        assert_eq!(size(4), size(1024));
        assert!(size(1024) < 128);
    }
}
