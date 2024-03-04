//! Reexporting the `constant` module according to the
//! current feature (Trezor model)

#[cfg(all(
    feature = "model_mercury",
    not(feature = "model_tr"),
    not(feature = "model_tt")
))]
pub use super::model_mercury::constant::*;
#[cfg(all(feature = "model_tr", not(feature = "model_tt")))]
pub use super::model_tr::constant::*;
#[cfg(all(feature = "model_tt", not(feature = "model_mercury")))]
pub use super::model_tt::constant::*;
