#[cfg(feature = "debug")]
use alloc::boxed::Box;

use crate::traits::crypto::CryptoError;
use crate::traits::util::{CoreServiceError, FastResult, ServiceResult};
use crate::traits::wire::FailureKind;

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
    InvalidMessage,
    InvalidArgument,
    ValueError(&'static str),
    /// Core asked the app to stop, the error must reach the app's entry point.
    Stopped,
    #[cfg(feature = "debug")]
    Context {
        file: &'static str,
        line: u32,
        source: Box<Error>,
    },
}

impl Error {
    /// The failure type Core reports to the host.
    pub fn kind(&self) -> FailureKind {
        match self {
            Self::ServiceError => FailureKind::ProcessError,
            Self::DataError(_) => FailureKind::DataError,
            Self::Cancelled => FailureKind::ActionCancelled,
            Self::InvalidMessage => FailureKind::DataError,
            Self::InvalidArgument => FailureKind::DataError,
            Self::ValueError(_) => FailureKind::DataError,
            // never reaches the host: the app exits instead
            Self::Stopped => FailureKind::ProcessError,
            #[cfg(feature = "debug")]
            Self::Context { source, .. } => source.kind(),
        }
    }

    /// The message Core reports to the host; tells apart variants sharing a
    /// code.
    pub fn message(&self) -> &'static str {
        match self {
            Self::ServiceError => "service error",
            Self::InvalidMessage => "invalid message",
            Self::InvalidArgument => "invalid argument",
            Self::DataError(msg) => msg,
            Self::ValueError(msg) => msg,
            Self::Cancelled => "cancelled",
            Self::Stopped => "stopped",
            #[cfg(feature = "debug")]
            Self::Context { source, .. } => source.message(),
        }
    }

    /// Whether Core asked the app to stop.
    pub fn is_stopped(&self) -> bool {
        match self {
            Self::Stopped => true,
            #[cfg(feature = "debug")]
            Self::Context { source, .. } => source.is_stopped(),
            _ => false,
        }
    }

    pub fn error_type(&self) -> &'static str {
        match self {
            Self::ServiceError => "ServiceError",
            Self::DataError(_) => "DataError",
            Self::Cancelled => "Cancelled",
            Self::InvalidMessage => "InvalidMessage",
            Self::InvalidArgument => "InvalidArgument",
            Self::ValueError(_) => "ValueError",
            Self::Stopped => "Stopped",
            #[cfg(feature = "debug")]
            Self::Context { source, .. } => source.error_type(),
        }
    }

    #[cfg(feature = "debug")]
    pub fn c_at(self, loc: &'static core::panic::Location<'static>) -> Self {
        Error::Context {
            file: loc.file(),
            line: loc.line(),
            source: Box::new(self),
        }
    }

    #[cfg(feature = "debug")]
    pub fn source(&self) -> Option<&Error> {
        match self {
            Error::Context { source, .. } => Some(&*source),
            _ => None,
        }
    }
}

impl CryptoError {
    /// Returns a static human-readable description of the error.
    pub fn message(&self) -> &'static str {
        match self {
            Self::InvalidPublicKey => "invalid public key",
            Self::InvalidSignature => "invalid signature",
            Self::InvalidEncoding => "invalid encoding",
        }
    }
}

impl<E> CoreServiceError<E> {
    /// Keeps the system errors, for services without errors of their own.
    pub(crate) fn system<F>(self) -> CoreServiceError<F> {
        match self {
            Self::ServiceError(_) | Self::ServiceCallFailed => CoreServiceError::ServiceCallFailed,
            Self::Timeout => CoreServiceError::Timeout,
            Self::StopApplication => CoreServiceError::StopApplication,
        }
    }
}

/// Splits a [`ServiceResult`] into its service-specific outcome and the
/// system errors, so the caller can match on the former and `?` the latter.
///
/// ```rust,ignore
/// match crypto.ecdsa_verify_digest(...).split_service_error()? {
///     Ok(()) => { ... }
///     Err(CryptoError::InvalidSignature) => { ... }
///     Err(_) => { ... }
/// }
/// ```
pub trait ServiceResultExt<T, E> {
    fn split_service_error(
        self,
    ) -> core::result::Result<core::result::Result<T, E>, CoreServiceError<()>>;
}

impl<T, E> ServiceResultExt<T, E> for ServiceResult<T, E> {
    fn split_service_error(
        self,
    ) -> core::result::Result<core::result::Result<T, E>, CoreServiceError<()>> {
        match self {
            FastResult::Ok(t) => Ok(Ok(t)),
            FastResult::Err(CoreServiceError::ServiceError(e)) => Ok(Err(e)),
            FastResult::Err(CoreServiceError::Timeout) => Err(CoreServiceError::Timeout),
            FastResult::Err(CoreServiceError::ServiceCallFailed) => {
                Err(CoreServiceError::ServiceCallFailed)
            }
            FastResult::Err(CoreServiceError::StopApplication) => {
                Err(CoreServiceError::StopApplication)
            }
        }
    }
}

impl From<CoreServiceError<()>> for Error {
    fn from(error: CoreServiceError<()>) -> Self {
        match error {
            CoreServiceError::StopApplication => Error::Stopped,
            // details are in Core's log
            CoreServiceError::ServiceError(())
            | CoreServiceError::Timeout
            | CoreServiceError::ServiceCallFailed => Error::ServiceError,
        }
    }
}

impl From<CryptoError> for Error {
    fn from(error: CryptoError) -> Self {
        Error::DataError(error.message())
    }
}

impl From<CoreServiceError<CryptoError>> for Error {
    fn from(error: CoreServiceError<CryptoError>) -> Self {
        match error {
            CoreServiceError::ServiceError(e) => e.into(),
            e => e.system::<()>().into(),
        }
    }
}

/// Converts the stable-ABI [`FastResult`] a [`WireV1`](crate::traits::wire::WireV1)/
/// [`CryptoV1`](crate::traits::crypto::CryptoV1)/[`UiV1`](crate::traits::ui::UiV1)
/// call returns into this crate's own [`Result`].
pub trait IntoAppResult<T> {
    fn into_app_result(self) -> Result<T>;
}

impl<T, E> IntoAppResult<T> for FastResult<T, E>
where
    Error: From<E>,
{
    fn into_app_result(self) -> Result<T> {
        self.into_result().map_err(Into::into)
    }
}

#[cfg(feature = "debug")]
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

#[cfg(not(feature = "debug"))]
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
    #[cfg(feature = "debug")]
    #[track_caller]
    fn c(self) -> Self {
        let loc = core::panic::Location::caller();
        self.map_err(|e| e.c_at(loc))
    }

    #[cfg(not(feature = "debug"))]
    fn c(self) -> Self {
        self
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stop_signal_survives_conversion() {
        assert!(Error::from(CoreServiceError::<()>::StopApplication).is_stopped());
        assert!(Error::from(CoreServiceError::<CryptoError>::StopApplication).is_stopped());
        assert!(!Error::from(CoreServiceError::<()>::ServiceCallFailed).is_stopped());
        assert!(!Error::DataError("stopped").is_stopped());
    }

    #[test]
    fn service_errors_convert() {
        let error = Error::from(CoreServiceError::ServiceError(
            CryptoError::InvalidSignature,
        ));
        assert_eq!(error.kind(), FailureKind::DataError);
        assert_eq!(error.message(), "invalid signature");
        let error = Error::from(CoreServiceError::<CryptoError>::Timeout);
        assert_eq!(error.kind(), FailureKind::ProcessError);
    }

    #[cfg(feature = "debug")]
    #[test]
    fn stop_signal_survives_context() {
        let error = Error::from(CoreServiceError::<()>::StopApplication)
            .c_at(core::panic::Location::caller());
        assert!(error.is_stopped());
    }
}
