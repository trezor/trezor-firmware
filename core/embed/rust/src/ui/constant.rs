//! Reexporting the `constant` module according to the
//! current feature (Trezor model)

#[cfg(all(
    feature = "layout_bolt",
    not(feature = "layout_delizia"),
    not(feature = "layout_caesar")
))]
pub use super::layout_bolt::constant::*;
#[cfg(all(feature = "layout_caesar", not(feature = "layout_delizia")))]
pub use super::layout_caesar::constant::*;
#[cfg(feature = "layout_delizia")]
pub use super::layout_delizia::constant::*;
