#[cfg(all(feature = "debug", feature = "app"))]
use crate::alloc_types::Box;
#[cfg(feature = "app")]
use crate::traits::crypto::CryptoError;
#[cfg(feature = "app")]
use crate::traits::util::FastResult;
#[cfg(feature = "app")]
use crate::traits::wire::WireError;

/// A wrapper which aligns its inner value to 8 bytes.
#[doc(hidden)]
#[repr(C, align(8))]
pub struct Align<T>(pub T);

pub type Result<T> = core::result::Result<T, Error>;

#[cfg_attr(any(feature = "debug", feature = "test"), derive(Debug))]
pub enum Error {
    ServiceError,
    DataError(&'static str),
    Cancelled,
    InvalidFunction,
    InvalidMessage,
    InvalidArgument,
    ValueError(&'static str),
    #[cfg(all(feature = "debug", feature = "app"))]
    Context {
        file: &'static str,
        line: u32,
        source: Box<Error>,
    },
}

impl Error {
    pub fn code(&self) -> u16 {
        match self {
            Self::ServiceError => 2,
            Self::DataError(_) => 3,
            Self::Cancelled => 4,
            Self::InvalidFunction => 5,
            Self::InvalidMessage => 6,
            Self::InvalidArgument => 7,
            Self::ValueError(_) => 8,
            #[cfg(all(feature = "debug", feature = "app"))]
            Self::Context { source, .. } => source.code(),
        }
    }

    pub fn message(&self) -> &'static str {
        match self {
            Self::ServiceError => "",
            Self::InvalidFunction => "",
            Self::InvalidMessage => "",
            Self::InvalidArgument => "",
            Self::DataError(msg) => msg,
            Self::ValueError(msg) => msg,
            Self::Cancelled => "",
            #[cfg(all(feature = "debug", feature = "app"))]
            Self::Context { source, .. } => source.message(),
        }
    }

    pub fn error_type(&self) -> &'static str {
        match self {
            Self::ServiceError => "ServiceError",
            Self::DataError(_) => "DataError",
            Self::Cancelled => "Cancelled",
            Self::InvalidFunction => "InvalidFunction",
            Self::InvalidMessage => "InvalidMessage",
            Self::InvalidArgument => "InvalidArgument",
            Self::ValueError(_) => "ValueError",
            #[cfg(all(feature = "debug", feature = "app"))]
            Self::Context { source, .. } => source.error_type(),
        }
    }

    #[cfg(all(feature = "debug", feature = "app"))]
    pub fn c_at(self, loc: &'static core::panic::Location<'static>) -> Self {
        Error::Context {
            file: loc.file(),
            line: loc.line(),
            source: Box::new(self),
        }
    }

    #[cfg(all(feature = "debug", feature = "app"))]
    pub fn source(&self) -> Option<&Error> {
        match self {
            Error::Context { source, .. } => Some(&*source),
            _ => None,
        }
    }
}

#[cfg(feature = "app")]
impl From<WireError> for Error {
    fn from(error: WireError) -> Self {
        Error::DataError(error.message())
    }
}

#[cfg(feature = "app")]
impl From<CryptoError> for Error {
    fn from(error: CryptoError) -> Self {
        Error::DataError(error.message())
    }
}

/// Converts the stable-ABI [`FastResult`] a [`WireV1`](crate::traits::wire::WireV1)/
/// [`CryptoV1`](crate::traits::crypto::CryptoV1)/[`UiV1`](crate::traits::ui::UiV1)
/// call returns into this crate's own [`Result`] — every wire call site was
/// hand-rolling `.into_result().map_err(Into::into)` for this.
#[cfg(feature = "app")]
pub trait IntoAppResult<T> {
    fn into_app_result(self) -> Result<T>;
}

#[cfg(feature = "app")]
impl<T> IntoAppResult<T> for FastResult<T, WireError> {
    fn into_app_result(self) -> Result<T> {
        self.into_result().map_err(Into::into)
    }
}

#[cfg(feature = "app")]
impl<T> IntoAppResult<T> for FastResult<T, CryptoError> {
    fn into_app_result(self) -> Result<T> {
        self.into_result().map_err(Into::into)
    }
}

#[cfg(all(feature = "debug", feature = "app"))]
impl ufmt::uDisplay for Error {
    fn fmt<W: ?Sized>(&self, f: &mut ufmt::Formatter<'_, W>) -> core::result::Result<(), W::Error>
    where
        W: ufmt::uWrite,
    {
        match self {
            Error::Context { file, line, .. } => {
                ufmt::uwrite!(f, "Context Error at\nLocation: {}:{}", file, line)?;
            }
            _ => {
                ufmt::uwrite!(f, "{}: {}", self.error_type(), self.message())?;
            }
        }
        let mut source = self.source();
        while let Some(err) = source {
            match err {
                Error::Context { file, line, .. } => {
                    ufmt::uwrite!(f, "\nLocation: {}:{}", file, line)?;
                }
                _ => {
                    ufmt::uwrite!(f, "\nCaused by: {}: {}", err.error_type(), err.message())?;
                }
            }
            source = err.source();
        }

        Ok(())
    }
}

#[cfg(not(all(feature = "debug", feature = "app")))]
impl ufmt::uDisplay for Error {
    fn fmt<W: ?Sized>(&self, f: &mut ufmt::Formatter<'_, W>) -> core::result::Result<(), W::Error>
    where
        W: ufmt::uWrite,
    {
        ufmt::uwrite!(f, "{}: {}", self.error_type(), self.message())?;
        Ok(())
    }
}

/// Extension trait for attaching call-site context to an [`Error`] as it
/// propagates up through `?`.
pub trait ResultExt<T> {
    /// Records the caller's file and line on `Err`, if the `debug` feature
    /// is enabled; otherwise a no-op.
    ///
    /// Call it right after any fallible expression you want to be locatable
    /// in a `debug` build, typically as `foo().c()?`:
    ///
    /// ```rust,no_run
    /// # use trezor_app_sdk::{Error, Result, ResultExt};
    /// fn inner() -> Result<()> {
    ///     Err(Error::InvalidArgument)
    /// }
    ///
    /// fn outer() -> Result<()> {
    ///     inner().c()?; // records this line when `debug` is enabled
    ///     Ok(())
    /// }
    /// ```
    ///
    /// # `debug` builds
    ///
    /// Wraps the error in [`Error::Context`], capturing the file and line of
    /// the `.c()` call itself via `#[track_caller]`. Every further `.c()`
    /// applied on the way back up the call stack adds one more location, so
    /// a chain of `.c()` calls builds a manual backtrace. Printing the final
    /// error (via its [`ufmt::uDisplay`] impl) walks that chain, e.g.:
    ///
    /// ```text
    /// Context Error at
    /// Location: outer.rs:8
    /// Location: main.rs:3
    /// Caused by: InvalidArgument:
    /// ```
    ///
    /// # Release builds
    ///
    /// Without the `debug` feature, `c()` just returns `self` unchanged —
    /// zero cost, so it's safe to sprinkle on every fallible expression
    /// regardless of build profile.
    ///
    /// # Gaps in the trace
    ///
    /// Each `.c()` call contributes exactly one location. If some function
    /// forwards an error without calling it (e.g. `foo()?` instead of
    /// `foo().c()?`), that hop simply contributes nothing — callers further
    /// up and callees further down that *do* call `.c()` still show up
    /// unaffected. In practice this matters most near the origin: since the
    /// error itself carries no location until something wraps it, if the
    /// call site closest to the failure skips `.c()`, the trace won't
    /// contain anything below the next ancestor that does call it — the
    /// backtrace effectively starts there. Call `.c()` consistently at every
    /// `?` in a chain to avoid these blind spots.
    fn c(self) -> Self;
}

impl<T> ResultExt<T> for Result<T> {
    #[cfg(all(feature = "debug", feature = "app"))]
    #[track_caller]
    fn c(self) -> Self {
        let loc = core::panic::Location::caller();
        self.map_err(|e| e.c_at(loc))
    }

    #[cfg(not(all(feature = "debug", feature = "app")))]
    fn c(self) -> Self {
        self
    }
}
