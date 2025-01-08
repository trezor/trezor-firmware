//! Reexporting the `constant` module according to the
//! current feature (Trezor model)

#[cfg(all(
    feature = "layout_bolt",
    not(feature = "layout_quicksilver"),
    not(feature = "layout_samson")
))]
pub use super::layout_bolt::constant::*;
#[cfg(all(feature = "layout_quicksilver", not(feature = "layout_bolt")))]
pub use super::layout_quicksilver::constant::*;
#[cfg(feature = "layout_samson")]
pub use super::layout_samson::constant::*;
