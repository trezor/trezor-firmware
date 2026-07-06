#[cfg(not(feature = "test"))]
use crate::low_level_api;
use crate::low_level_api::ApiError;
use crate::service;
#[cfg(not(feature = "test"))]
use crate::{CORE_SERVICE, core_services, error, util};

/// A wrapper which aligns its inner value to 8 bytes.
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
        context: &'static str,
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
    pub fn context(self, context: &'static str) -> Self {
        Error::Context {
            context,
            source: Box::new(self),
        }
    }

    #[cfg(not(feature = "debug"))]
    pub fn context(self, _context: &'static str) -> Self {
        self
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
            Error::Context { context, .. } => {
                ufmt::uwrite!(f, "{}", context)?;
            }
            _ => {
                ufmt::uwrite!(f, "{}: {}", self.error_type(), self.message())?;
            }
        }
        let mut source = self.source();
        while let Some(err) = source {
            match err {
                Error::Context { context, .. } => {
                    ufmt::uwrite!(f, "\nCaused by: {}", context)?;
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

pub trait ResultExt<T> {
    fn context(self, context: &'static str) -> Self;
}

impl<T> ResultExt<T> for Result<T> {
    fn context(self, context: &'static str) -> Self {
        self.map_err(|e| e.context(context))
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

#[cfg(all(feature = "debug", not(feature = "test")))]
#[lang = "eh_personality"]
fn eh_personality() -> ! {
    loop {}
}

#[cfg(all(feature = "debug", not(feature = "test")))]
#[unsafe(no_mangle)]
unsafe extern "C" fn _Unwind_Resume() {
    unsafe { core::intrinsics::unreachable() };
}
