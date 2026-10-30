//! One fact for the person to read. The public docs live on [`Field`].
//!
//! A fact is what it is, never how it looks: the constructor names the kind of
//! value, and core decides the styling, the grouping and the paging of that kind
//! on every model. Nothing here holds behaviour.

use crate::modui::call::set_source_error;
use crate::structs::{FieldKind, OptStrSlice, Slice, Source, WireField};
use crate::{Error, Result};

/// One thing the person reads: a label and a value, or a sentence on its own.
///
/// What a fact *is* decides how it looks, on every model; the app never picks a
/// style. A list of facts can mix all six kinds, a warning included.
///
/// | Constructor | For | Example |
/// |---|---|---|
/// | [`text`](Field::text) | Words or a number, shown as written. | `Field::text("Resource", "Energy")` |
/// | [`amount`](Field::amount) | A sum with its unit, already formatted by the app. | `Field::amount("Amount", "1.5 TRX")` |
/// | [`address`](Field::address) | Something compared character by character. | `Field::address("Recipient", &to)` |
/// | [`data`](Field::data) | Raw bytes of any length, shown as hex and paged. | `Field::data("Input data", &calldata)` |
/// | [`data_source`](Field::data_source) | Raw bytes the app hands out while core reads them, shown as hex and paged. | `Field::data_source("Input data", len, &source)` |
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
///     Field::amount("Amount", "1,000 TRX"),
///     Field::text("Resource", "Energy"),
/// ];
/// ```
#[derive(Copy, Clone)]
#[repr(transparent)]
pub struct Field<'a> {
    wire: WireField<'a>,
}

/// Where a [`data_source`](Field::data_source) field's bytes come from, read by
/// core while the person pages.
///
/// Core reads in order, from offset 0, in contiguous ranges, and asks for each
/// range once, so a source may hash what it hands out. It stops when the person
/// reaches the end of the field or refuses it.
///
/// `read` takes `&self` so that a [`Field`] stays `Copy`: a source that keeps
/// state keeps it in a `Cell` or `RefCell` of its own.
pub trait DataSource {
    /// Fills `buf` with the bytes starting at `offset`.
    fn read(&self, offset: u32, buf: &mut [u8]) -> Result<()>;
}

impl DataSource for [u8] {
    fn read(&self, offset: u32, buf: &mut [u8]) -> Result<()> {
        let start = offset as usize;
        let end = start
            .checked_add(buf.len())
            .ok_or(Error::DataError("a data source read past its end"))?;
        let bytes = self
            .get(start..end)
            .ok_or(Error::DataError("a data source read past its end"))?;
        buf.copy_from_slice(bytes);
        Ok(())
    }
}

impl<T: DataSource + ?Sized> DataSource for &T {
    fn read(&self, offset: u32, buf: &mut [u8]) -> Result<()> {
        (**self).read(offset, buf)
    }
}

/// Copies out of a `&[u8]` whose length is `total`.
///
/// Not `read_source::<[u8]>`: a thin pointer cannot rebuild a slice, so the
/// length comes from `Source::total` instead.
extern "C" fn read_bytes(ctx: *const u8, offset: u32, total: u32, buf: *mut u8, len: u32) -> i32 {
    // SAFETY: `ctx` and `total` come from `Source::new` in `Field::data`, for a
    // slice that outlives the request; `buf` and `len` come from core's chunk
    // buffer.
    let bytes = unsafe { core::slice::from_raw_parts(ctx, total as usize) };
    let buf = unsafe { core::slice::from_raw_parts_mut(buf, len as usize) };
    match <[u8] as DataSource>::read(bytes, offset, buf) {
        Ok(()) => 0,
        Err(e) => {
            set_source_error(e);
            -1
        }
    }
}

/// Reads the `D` at `ctx`.
extern "C" fn read_source<D: DataSource>(
    ctx: *const u8,
    offset: u32,
    _total: u32,
    buf: *mut u8,
    len: u32,
) -> i32 {
    // SAFETY: `ctx` comes from `Source::new` in `Field::data_source`, for a `D`
    // that outlives the request; `buf` and `len` come from core's chunk buffer.
    let source = unsafe { &*ctx.cast::<D>() };
    let buf = unsafe { core::slice::from_raw_parts_mut(buf, len as usize) };
    match source.read(offset, buf) {
        Ok(()) => 0,
        Err(e) => {
            set_source_error(e);
            -1
        }
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
        Self::new(FieldKind::Text, Some(label), value.as_bytes())
    }

    /// A sum with its unit, already formatted by the app.
    ///
    /// Core does not do the arithmetic or pick the unit; the app writes the
    /// number as the person should read it. Under
    /// [`Review::confirm_final`](crate::modui::Review::confirm_final) an amount
    /// gets the summary styling.
    ///
    /// # Example
    ///
    /// ```no_run
    /// use trezor_app_sdk::modui::Field;
    ///
    /// let amount = Field::amount("Amount", "1.5 TRX");
    /// ```
    pub fn amount(label: &'a str, value: &'a str) -> Self {
        Self::new(FieldKind::Amount, Some(label), value.as_bytes())
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
        Self::new(FieldKind::Address, Some(label), value.as_bytes())
    }

    /// Raw bytes of any length, shown as hex and paged.
    ///
    /// At most one per review. Core pulls the bytes from the app in chunks
    /// while the person pages, so the app hands over the whole value and never
    /// learns how many chunks it took.
    ///
    /// # Example
    ///
    /// ```no_run
    /// use trezor_app_sdk::modui::Field;
    ///
    /// let data = Field::data("Input data", &[0xde, 0xad, 0xbe, 0xef]);
    /// ```
    pub fn data(label: &'a str, value: &'a [u8]) -> Self {
        Self::wire_data(
            label,
            Source::new(value.as_ptr(), value.len() as u32, false, read_bytes),
        )
    }

    /// Raw bytes the app does not hold all at once, shown as hex and paged.
    ///
    /// At most one per review, like [`data`](Field::data). It may not sit in an
    /// extra: an extra can be opened again, and its bytes would be read again.
    /// That is [`Error::DataError`] with
    /// `"a streamed data field cannot be in an extra"`.
    ///
    /// Core reads the source while the person pages, **in order, from offset 0,
    /// in contiguous ranges, each range once**, and stops when the person reaches
    /// the end or refuses. A source may therefore hash what it hands out. `read`
    /// takes `&self`, so a source that keeps state keeps it in a `Cell` or
    /// `RefCell` of its own.
    ///
    /// If `read` fails, the review ends as refused and the app gets the source's
    /// own error back, not [`Error::Cancelled`](crate::Error::Cancelled).
    ///
    /// `len` is the total number of bytes, the source's to know.
    ///
    /// A trait object works too: `&dyn DataSource` is itself a `DataSource`
    /// through the blanket `impl for &T`, so pass it as `&source`.
    ///
    /// # Example
    ///
    /// ```no_run
    /// use core::cell::RefCell;
    /// use core::fmt::Write as _;
    /// use trezor_app_sdk::crypto::{self as sdk, HasherExt, HashingAlgorithm};
    /// use trezor_app_sdk::modui::{self, DataSource, Field};
    /// use trezor_app_sdk::traits::crypto::BoxedHasher;
    /// use trezor_app_sdk::{Error, Result};
    ///
    /// /// Bytes as the host streams them, hashed on the way out.
    /// struct Stream<'a> {
    ///     bytes: &'a [u8],
    ///     hasher: RefCell<BoxedHasher>,
    /// }
    ///
    /// impl DataSource for Stream<'_> {
    ///     fn read(&self, offset: u32, buf: &mut [u8]) -> Result<()> {
    ///         let start = offset as usize;
    ///         let end = start + buf.len();
    ///         let bytes = self.bytes.get(start..end).ok_or(Error::DataError("out of bytes"))?;
    ///         buf.copy_from_slice(bytes);
    ///         self.hasher.borrow_mut().update(buf);
    ///         Ok(())
    ///     }
    /// }
    ///
    /// fn confirm_stream(bytes: &[u8]) -> Result<()> {
    ///     let stream = Stream {
    ///         bytes,
    ///         hasher: RefCell::new(sdk::get_hasher(HashingAlgorithm::Sha256)),
    ///     };
    ///     let field = Field::data_source("Input data", bytes.len() as u32, &stream);
    ///     modui::review("stream", "Stream", &[field]).confirm()?;
    ///
    ///     let digest = stream.hasher.borrow_mut().finalize();
    ///     let mut hash = String::new();
    ///     for byte in digest.as_ref() {
    ///         let _ = write!(hash, "{:02x}", byte);
    ///     }
    ///     modui::review("summary", "Signed", &[Field::address("Hash", &hash)]).confirm_final()
    /// }
    /// ```
    pub fn data_source<D: DataSource + 'a>(label: &'a str, len: u32, source: &'a D) -> Self {
        Self::wire_data(
            label,
            Source::new(source as *const D as *const u8, len, true, read_source::<D>),
        )
    }

    fn wire_data(label: &'a str, source: Source<'a>) -> Self {
        Self {
            wire: WireField {
                kind: FieldKind::Data,
                label: OptStrSlice::new(Some(label)),
                value: Slice::new(&[]),
                len: source.total(),
                source: Some(source),
            },
        }
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
        Self::new(FieldKind::Note, None, text.as_bytes())
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
        Self::new(FieldKind::Warning, None, text.as_bytes())
    }

    fn new(kind: FieldKind, label: Option<&'a str>, value: &'a [u8]) -> Self {
        Self {
            wire: WireField {
                kind,
                label: OptStrSlice::new(label),
                value: Slice::new(value),
                len: value.len() as u32,
                source: None,
            },
        }
    }

    pub(crate) fn kind(&self) -> FieldKind {
        self.wire.kind
    }

    pub(crate) fn byte_len(&self) -> u32 {
        self.wire.len
    }

    pub(crate) fn is_streamed(&self) -> bool {
        self.wire.is_streamed()
    }
}

/// A list of facts, as a request carries them.
///
/// `Field` is a `#[repr(transparent)]` wrapper around `WireField`, so the two
/// lists have the same layout and the borrow is only a cast.
pub(crate) fn wire_fields<'a>(fields: &'a [Field<'a>]) -> Slice<'a, WireField<'a>> {
    // SAFETY: `Field` is `#[repr(transparent)]` over `WireField`, so a
    // `&[Field]` has the layout of a `&[WireField]` of the same length.
    let wire = unsafe {
        core::slice::from_raw_parts(fields.as_ptr().cast::<WireField<'a>>(), fields.len())
    };
    Slice::new(wire)
}

/// Checks what a request can carry before it is built: at most one
/// [`data`](Field::data) field.
///
/// The bytes themselves are not limited: core pulls them from the app, so the
/// request only carries their length.
pub(crate) fn check_fields(fields: &[Field<'_>]) -> Result<()> {
    let mut data = 0;
    for field in fields {
        if field.kind() != FieldKind::Data {
            continue;
        }
        data += 1;
    }
    if data > 1 {
        return Err(Error::DataError("more than one data field"));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_note_carries_its_text_and_no_label() {
        let note = Field::note("Continue?");
        assert!(note.kind() == FieldKind::Note);
        assert_eq!(note.byte_len(), "Continue?".len() as u32);
        assert_eq!(note.wire.label.as_str(), None);
        assert_eq!(note.wire.value.as_slice(), b"Continue?");
    }

    #[test]
    fn text_facts_carry_their_label_and_bytes() {
        let amount = Field::amount("Amount", "1.5 TRX");
        assert!(amount.kind() == FieldKind::Amount);
        assert_eq!(amount.wire.label.as_str(), Some("Amount"));
        assert_eq!(amount.byte_len(), "1.5 TRX".len() as u32);
    }

    #[test]
    fn a_second_data_field_is_refused() {
        let fields = [Field::data("a", &[1]), Field::data("b", &[2])];
        assert!(matches!(
            check_fields(&fields),
            Err(Error::DataError("more than one data field"))
        ));
    }

    #[test]
    fn data_of_any_length_is_accepted() {
        let bytes = [0u8; 4096];
        let fields = [Field::data("a", &bytes)];
        assert!(check_fields(&fields).is_ok());
        assert_eq!(fields[0].byte_len(), 4096);
    }

    #[test]
    fn one_data_field_beside_text_is_accepted() {
        let fields = [Field::data("a", &[1, 2, 3]), Field::text("b", "c")];
        assert!(check_fields(&fields).is_ok());
    }

    #[test]
    fn the_slice_source_returns_the_right_ranges() {
        let bytes = b"hello";
        let mut buf = [0u8; 3];
        <[u8] as DataSource>::read(bytes, 1, &mut buf).unwrap();
        assert_eq!(&buf, b"ell");
        assert!(<[u8] as DataSource>::read(bytes, 4, &mut buf).is_err());
    }

    #[test]
    fn the_request_does_not_grow_with_the_data() {
        use crate::structs::{ReviewRequest, TrezorUiEnum};

        fn size(bytes: &[u8]) -> usize {
            let fields = [Field::data("a", bytes)];
            let request = TrezorUiEnum::Review(ReviewRequest {
                step: "s".into(),
                title: "t".into(),
                fields: wire_fields(&fields),
                extras: Slice::new(&[]),
                is_final: false,
            });
            rkyv::to_bytes::<rkyv::rancor::Error>(&request)
                .unwrap()
                .len()
        }

        assert_eq!(size(&[0u8; 4]), size(&[0u8; 1024]));
        assert!(size(&[0u8; 1024]) < 128);
    }
}
