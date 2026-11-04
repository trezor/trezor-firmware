#[stabby::stabby]
#[repr(C, u8)]
pub enum FastResult<T, E> {
    Ok(T) = 0,
    Err(E) = 1,
}

impl<T, E> FastResult<T, E> {
    pub fn into_result(self) -> Result<T, E> {
        match self {
            FastResult::Ok(t) => Result::Ok(t),
            FastResult::Err(e) => Result::Err(e),
        }
    }

    pub fn as_result_ref<'a>(&'a self) -> Result<&'a T, &'a E> {
        match self {
            FastResult::Ok(t) => Result::Ok(t),
            FastResult::Err(e) => Result::Err(e),
        }
    }
}

impl<T, E> From<Result<T, E>> for FastResult<T, E> {
    fn from(result: Result<T, E>) -> Self {
        match result {
            Result::Ok(t) => FastResult::Ok(t),
            Result::Err(e) => FastResult::Err(e),
        }
    }
}

/// Errors that can occur while talking to a Core-provided service.
///
/// Primary error type for fallible API calls.
#[stabby::stabby]
#[repr(C, u8)]
pub enum CoreServiceError<E> {
    /// Service-specific error.
    ServiceError(E),
    /// The operation timed out while waiting for a response.
    Timeout,
    /// Failed to perform the operation.
    ///
    /// Could be an IPC failure, invalid arguments or undecodable response.
    /// Core-side logging provides details, those are not passed over the API
    /// boundary.
    ServiceCallFailed,
    /// Core requested the application to stop.
    ///
    /// This error MUST be propagated to the top-level handler and end the
    /// application event loop.
    StopApplication,
}

/// Result of an API call that goes through a Core service.
pub type ServiceResult<T, E = ()> = FastResult<T, CoreServiceError<E>>;

impl<E> CoreServiceError<E> {
    /// Keeps the system errors, for services without errors of their own.
    pub fn system<F>(self) -> CoreServiceError<F> {
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
/// match crypto.check_address_mac(...).split_service_error()? {
///     Ok(()) => { ... }
///     Err(CryptoError::InvalidMac) => { ... }
///     Err(_) => { ... }
/// }
/// ```
pub trait ServiceResultExt<T, E> {
    fn split_service_error(self) -> Result<Result<T, E>, CoreServiceError<()>>;
}

impl<T, E> ServiceResultExt<T, E> for ServiceResult<T, E> {
    fn split_service_error(self) -> Result<Result<T, E>, CoreServiceError<()>> {
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

/// Longest timeout, in milliseconds, an API call accepts.
pub const TIMEOUT_MAX: u32 = u32::MAX / 2 - 1;
