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
impl From<UIError> for crate::micropython::Error {
    fn from(error: UIError) -> Self {
        match error {
            UIError::InvalidValue => crate::micropython::Error::ValueError(c"Invalid value"),
            UIError::Capacity => crate::micropython::Error::ValueError(c"Container overflow"),
            UIError::BufferLocked => crate::micropython::Error::RuntimeError(c"Buffer locked"),
        }
    }
}
