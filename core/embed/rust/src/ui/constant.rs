//! Reexporting the `constant` module according to the
//! current feature (Trezor model)

#[cfg(feature = "model_t1")]
pub use super::model_t1::constant::*;
#[cfg(all(feature = "model_tr", not(feature = "model_t1")))]
pub use super::model_tr::constant::*;
#[cfg(all(
    feature = "model_tt",
    not(feature = "model_tr"),
    not(feature = "model_t1")
))]
pub use super::model_tt::constant::*;
