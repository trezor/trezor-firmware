use core::num::TryFromIntError;

pub enum UIError {
    /// Invalid numeric value for conversion to an internal type.
    InvalidValue,
    /// Internal buffer (string, vec) is full.
    Capacity,
    /// Internal buffer is locked by another user.
    BufferLocked,
}

impl From<heapless::CapacityError> for UIError {
    fn from(_: heapless::CapacityError) -> Self {
        UIError::Capacity
    }
}

impl From<TryFromIntError> for UIError {
    fn from(_: TryFromIntError) -> Self {
        UIError::InvalidValue
    }
}

#[cfg(feature = "micropython")]
impl From<UIError> for micropython::Error {
    fn from(error: UIError) -> Self {
        match error {
            UIError::InvalidValue => micropython::Error::ValueError(c"Invalid value"),
            UIError::Capacity => micropython::Error::ValueError(c"Container overflow"),
            UIError::BufferLocked => micropython::Error::RuntimeError(c"Buffer locked"),
        }
    }
}
