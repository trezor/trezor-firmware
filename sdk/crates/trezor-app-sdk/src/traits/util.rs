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

/// Longest timeout, in milliseconds, an API call accepts.
pub const TIMEOUT_MAX: u32 = u32::MAX / 2 - 1;
