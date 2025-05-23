//! Reexporting the `constant` module according to the
//! current feature (Trezor model)

cfg_if::cfg_if! {
    if #[cfg(feature = "layout_bolt")] {
        pub use super::layout_bolt::constant::*;
    } else if #[cfg(feature = "layout_caesar")] {
        pub use super::layout_caesar::constant::*;
    } else if #[cfg(feature = "layout_delizia")] {
        pub use super::layout_delizia::constant::*;
    } else if #[cfg(feature = "layout_eckhart")] {
        pub use super::layout_eckhart::constant::*;
    }
}
