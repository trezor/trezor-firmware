//! The primitives the request types are built from: borrowed strings and
//! slices that are both stabby, so they cross a vtable as they are, and rkyv,
//! so `core/embed/api` serializes them for IPC.
//!
//! The UI request types themselves are in [`crate::traits::ui`].

use rkyv::boxed::{ArchivedBox, BoxResolver};
use rkyv::option::ArchivedOption;
use rkyv::rancor::Fallible;
use rkyv::ser::Writer;
use rkyv::{Archive, Place, Serialize, SerializeUnsized};
use stabby::IStable;
use stabby::slice::Slice as StabbySlice;
use stabby::str::Str;

// ============================================================================
// Field types
// ============================================================================
//
// Every request type below is both `#[stabby::stabby]` and rkyv `Archive`: an
// app passes it through the `UiV1` vtable as-is, and `core/embed/api`
// serializes that same value for IPC. These three field types make that work:
// each holds stabby's FFI-safe form and archives as the rkyv type core reads.

/// A borrowed string: stabby `Str` across the FFI, `ArchivedBox<str>` on the
/// wire.
#[stabby::stabby]
#[derive(Copy, Clone, PartialEq, Eq)]
pub struct StrSlice<'a> {
    inner: Str<'a>,
}

impl<'a> StrSlice<'a> {
    /// Borrows `s`.
    pub const fn new(s: &'a str) -> Self {
        Self { inner: Str::new(s) }
    }

    /// The borrowed string.
    pub fn as_str(&self) -> &'a str {
        self.inner.as_str()
    }
}

// ufmt deliberately doesn't implement uDebug for `str`, so this writes the raw
// contents, matching ufmt's own `uDisplay for str`.
impl<'a> ufmt::uDebug for StrSlice<'a> {
    fn fmt<W: ?Sized>(&self, f: &mut ufmt::Formatter<'_, W>) -> Result<(), W::Error>
    where
        W: ufmt::uWrite,
    {
        f.write_str(self.as_str())
    }
}

impl<'a> From<&'a str> for StrSlice<'a> {
    fn from(s: &'a str) -> Self {
        Self::new(s)
    }
}

// Archives as rkyv's own `ArchivedBox<str>`, whose `CheckBytes` core uses to
// validate a request.
impl<'a> Archive for StrSlice<'a> {
    type Archived = ArchivedBox<str>;
    type Resolver = BoxResolver;

    fn resolve(&self, resolver: Self::Resolver, out: Place<Self::Archived>) {
        ArchivedBox::resolve_from_ref(self.as_str(), resolver, out)
    }
}

impl<'a, S: Fallible + Writer + ?Sized> Serialize<S> for StrSlice<'a> {
    fn serialize(&self, serializer: &mut S) -> Result<Self::Resolver, S::Error> {
        ArchivedBox::serialize_from_ref(self.as_str(), serializer)
    }
}

/// An optional borrowed string. Archives exactly as `Option<StrSlice>` would.
///
/// Not a stabby `Option<Str>`: stabby cannot niche that, and its `Option`
/// is not `Copy`. A flag next to the bytes is both.
#[stabby::stabby]
#[derive(Copy, Clone, PartialEq, Eq)]
pub struct OptStrSlice<'a> {
    inner: Str<'a>,
    some: bool,
}

impl<'a> OptStrSlice<'a> {
    /// No string.
    pub const NONE: Self = Self {
        inner: Str::new(""),
        some: false,
    };

    /// Borrows `s`, if any.
    pub const fn new(s: Option<&'a str>) -> Self {
        match s {
            Some(s) => Self {
                inner: Str::new(s),
                some: true,
            },
            None => Self::NONE,
        }
    }

    /// The borrowed string, if any.
    pub fn as_str(&self) -> Option<&'a str> {
        self.some.then(|| self.inner.as_str())
    }

    fn as_slice(&self) -> Option<StrSlice<'a>> {
        self.as_str().map(StrSlice::new)
    }
}

impl<'a> ufmt::uDebug for OptStrSlice<'a> {
    fn fmt<W: ?Sized>(&self, f: &mut ufmt::Formatter<'_, W>) -> Result<(), W::Error>
    where
        W: ufmt::uWrite,
    {
        self.as_slice().fmt(f)
    }
}

impl<'a> From<Option<&'a str>> for OptStrSlice<'a> {
    fn from(s: Option<&'a str>) -> Self {
        Self::new(s)
    }
}

impl<'a> Archive for OptStrSlice<'a> {
    type Archived = ArchivedOption<ArchivedBox<str>>;
    type Resolver = Option<BoxResolver>;

    fn resolve(&self, resolver: Self::Resolver, out: Place<Self::Archived>) {
        self.as_slice().resolve(resolver, out)
    }
}

impl<'a, S: Fallible + Writer + ?Sized> Serialize<S> for OptStrSlice<'a> {
    fn serialize(&self, serializer: &mut S) -> Result<Self::Resolver, S::Error> {
        self.as_slice().serialize(serializer)
    }
}

/// A borrowed slice: stabby `Slice` across the FFI, `ArchivedBox<[T]>` on the
/// wire.
#[stabby::stabby]
pub struct Slice<'a, T: IStable> {
    inner: StabbySlice<'a, T>,
}

// Manual Copy/Clone: only the borrow is copied, never the elements.
impl<'a, T: IStable> Copy for Slice<'a, T> {}

impl<'a, T: IStable> Clone for Slice<'a, T> {
    fn clone(&self) -> Self {
        *self
    }
}

impl<'a, T: IStable + ufmt::uDebug> ufmt::uDebug for Slice<'a, T> {
    fn fmt<W: ?Sized>(&self, f: &mut ufmt::Formatter<'_, W>) -> Result<(), W::Error>
    where
        W: ufmt::uWrite,
    {
        self.as_slice().fmt(f)
    }
}

impl<'a, T: IStable + PartialEq> PartialEq for Slice<'a, T> {
    fn eq(&self, other: &Self) -> bool {
        self.as_slice() == other.as_slice()
    }
}

impl<'a, T: IStable + Eq> Eq for Slice<'a, T> {}

impl<'a, T: IStable> Slice<'a, T> {
    /// Borrows `s`.
    pub fn new(s: &'a [T]) -> Self {
        Self { inner: s.into() }
    }

    /// The borrowed slice.
    pub fn as_slice(&self) -> &'a [T] {
        self.inner.as_slice()
    }

    /// Number of elements.
    pub fn len(&self) -> usize {
        self.inner.len()
    }

    /// Whether there are no elements.
    pub fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }
}

impl<'a, T: IStable> From<&'a [T]> for Slice<'a, T> {
    fn from(s: &'a [T]) -> Self {
        Self::new(s)
    }
}

// Archives as rkyv's own `ArchivedBox<[T::Archived]>`, for the same reason as
// `StrSlice`.
impl<'a, T: IStable + Archive> Archive for Slice<'a, T> {
    type Archived = ArchivedBox<[T::Archived]>;
    type Resolver = BoxResolver;

    fn resolve(&self, resolver: Self::Resolver, out: Place<Self::Archived>) {
        ArchivedBox::resolve_from_ref(self.as_slice(), resolver, out)
    }
}

impl<'a, T: IStable + Archive, S: Fallible + Writer + ?Sized> Serialize<S> for Slice<'a, T>
where
    [T]: SerializeUnsized<S>,
{
    fn serialize(&self, serializer: &mut S) -> Result<Self::Resolver, S::Error> {
        ArchivedBox::serialize_from_ref(self.as_slice(), serializer)
    }
}
