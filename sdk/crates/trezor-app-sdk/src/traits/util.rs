use ufmt::derive::uDebug;

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

/// Represents a timeout duration in milliseconds.
///
/// Use [`Timeout::max`] for the longest supported timeout, or construct
/// via [`Timeout::ms`], [`Timeout::seconds`], or [`Timeout::minutes`].
#[derive(uDebug, Copy, Clone, PartialEq, Eq)]
pub struct Timeout(pub(crate) u32);

pub const TIMEOUT_MAX: u32 = u32::MAX / 2 - 1;

impl Timeout {
    /// Creates a timeout of `ms` milliseconds.
    ///
    /// # Panics
    ///
    /// Panics if `ms` exceeds [`TIMEOUT_MAX`].
    pub fn ms(ms: u32) -> Self {
        assert!(ms <= TIMEOUT_MAX, "Timeout too long");
        Self(ms)
    }

    /// Creates a timeout of `seconds` seconds.
    ///
    /// # Panics
    ///
    /// Panics if the resulting timeout exceeds [`TIMEOUT_MAX`] ms.
    pub fn seconds(seconds: u32) -> Self {
        Self::ms(seconds * 1000)
    }

    /// Creates a timeout of `minutes` minutes.
    ///
    /// # Panics
    ///
    /// Panics if the resulting timeout exceeds [`TIMEOUT_MAX`] ms.
    pub fn minutes(minutes: u32) -> Self {
        Self::seconds(minutes * 60)
    }

    /// Returns the maximum supported timeout value.
    pub fn max() -> Self {
        Self::ms(TIMEOUT_MAX)
    }

    pub fn as_ms(&self) -> u32 {
        self.0
    }
}
