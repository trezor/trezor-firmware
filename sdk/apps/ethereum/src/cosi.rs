use trezor_app_sdk::{Error, Result};

/// CoSi verification left the SDK; Core will verify definitions itself.
/// Until then every external definition is rejected.
pub fn verify(
    _signature: &[u8; 64],
    _data: &[u8],
    _threshold: usize,
    _keys: &[&[u8; 32]],
    _sigmask: u8,
) -> Result<bool> {
    Err(Error::DataError("External definitions are not supported"))
}
