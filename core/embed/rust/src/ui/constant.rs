//! Reexporting the `constant` module according to the
//! current feature (Trezor model)

#[cfg(all(
    feature = "model_lincoln",
    not(any(feature = "model_mercury", feature = "model_tr", feature = "model_tt"))
))]
pub use super::model_lincoln::constant::*;
#[cfg(all(
    feature = "model_mercury",
    not(any(feature = "model_tr", feature = "model_tt"),)
))]
pub use super::model_mercury::constant::*;
#[cfg(all(feature = "model_tr", not(feature = "model_tt")))]
pub use super::model_tr::constant::*;
#[cfg(feature = "model_tt")]
pub use super::model_tt::constant::*;
