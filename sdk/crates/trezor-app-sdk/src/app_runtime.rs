#[cfg(feature = "debug")]
use crate::alloc_types::Box;
#[cfg(not(feature = "test"))]
use crate::low_level_api;
use crate::low_level_api::ApiError;
use crate::service;
#[cfg(not(feature = "test"))]
use crate::{CORE_SERVICE, core_services, error, util};

/// A wrapper which aligns its inner value to 8 bytes.
#[doc(hidden)]
#[repr(C, align(8))]
pub struct Align<T>(pub T);

pub type Result<T> = core::result::Result<T, Error>;

#[cfg_attr(any(feature = "debug", feature = "test"), derive(Debug))]
pub enum Error {
    ApiError(ApiError),
    ServiceError,
    DataError(&'static str),
    Cancelled,
    InvalidFunction,
    InvalidMessage,
    InvalidArgument,
    ValueError(&'static str),
    #[cfg(feature = "debug")]
    Context {
        file: &'static str,
        line: u32,
        source: Box<Error>,
    },
}

impl Error {
    pub fn code(&self) -> u16 {
        match self {
            Self::ApiError(_) => 1,
            Self::ServiceError => 2,
            Self::DataError(_) => 3,
            Self::Cancelled => 4,
            Self::InvalidFunction => 5,
            Self::InvalidMessage => 6,
            Self::InvalidArgument => 7,
            Self::ValueError(_) => 8,
            #[cfg(feature = "debug")]
            Self::Context { source, .. } => source.code(),
        }
    }

    pub fn message(&self) -> &'static str {
        match self {
            Self::ApiError(_) => "",
            Self::ServiceError => "",
            Self::InvalidFunction => "",
            Self::InvalidMessage => "",
            Self::InvalidArgument => "",
            Self::DataError(msg) => msg,
            Self::ValueError(msg) => msg,
            Self::Cancelled => "",
            #[cfg(feature = "debug")]
            Self::Context { source, .. } => source.message(),
        }
    }

    pub fn error_type(&self) -> &'static str {
        match self {
            Self::ApiError(_) => "ApiError",
            Self::ServiceError => "ServiceError",
            Self::DataError(_) => "DataError",
            Self::Cancelled => "Cancelled",
            Self::InvalidFunction => "InvalidFunction",
            Self::InvalidMessage => "InvalidMessage",
            Self::InvalidArgument => "InvalidArgument",
            Self::ValueError(_) => "ValueError",
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

impl From<ApiError> for Error {
    fn from(error: ApiError) -> Self {
        Error::ApiError(error)
    }
}

impl From<service::Error<'_>> for Error {
    fn from(_error: service::Error) -> Self {
        Error::ServiceError
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

#[cfg(not(feature = "test"))]
use embedded_alloc::LlffHeap as Heap;

#[cfg(not(feature = "test"))]
#[global_allocator]
static HEAP: Heap = Heap::empty();

#[cfg(not(feature = "test"))]
unsafe extern "Rust" {
    unsafe fn app() -> Result<()>;
}

#[cfg(not(feature = "test"))]
#[unsafe(no_mangle)]
pub unsafe extern "C" fn applet_main(
    api_get: low_level_api::ffi::trezor_api_getter_t,
) -> core::ffi::c_int {
    unsafe { low_level_api::init(api_get) };

    CORE_SERVICE.start();
    core_services::init(&CORE_SERVICE);

    {
        use core::mem::MaybeUninit;
        const HEAP_SIZE: usize = 16 * 1024; // 16 KiB
        static mut HEAP_MEM: [MaybeUninit<u8>; HEAP_SIZE] = [MaybeUninit::uninit(); HEAP_SIZE];
        unsafe { HEAP.init(&raw mut HEAP_MEM as usize, HEAP_SIZE) }
    }

    let result = unsafe { app() };

    match result {
        Ok(()) => {
            _ = low_level_api::system_exit();
        }
        Err(e) => {
            error!("Application error");
            let mut error_buf = [0u8; 256];
            let mut writer = util::SliceWriter::new(&mut error_buf);
            _ = ufmt::uwrite!(
                writer,
                "Application failed with error type: {} code: {} and message: {}",
                e.error_type(),
                e.code(),
                e.message()
            );
            error!("{}", e);
            _ = low_level_api::system_exit_error("Error", writer.as_ref(), "");
        }
    }
}

#[cfg(all(feature = "debug", not(feature = "test")))]
#[panic_handler]
fn panic_handler(info: &core::panic::PanicInfo<'_>) -> ! {
    let msg = info.message().as_str().unwrap_or("PANIC");
    let (file, line) = info
        .location()
        .map(|loc| {
            let file = loc.file();
            let file_short = file.rsplit('/').next().unwrap_or(file);
            (file_short, loc.line() as i32)
        })
        .unwrap_or(("<unknown>", 0));
    low_level_api::system_exit_fatal(msg, file, line);
}

#[cfg(all(feature = "debug", not(feature = "test"), feature = "nightly"))]
#[lang = "eh_personality"]
fn eh_personality() -> ! {
    loop {}
}

#[cfg(all(feature = "debug", not(feature = "test"), feature = "nightly"))]
#[unsafe(no_mangle)]
unsafe extern "C" fn _Unwind_Resume() {
    unsafe { core::intrinsics::unreachable() };
}
