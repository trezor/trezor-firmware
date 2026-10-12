//! Blocks that ask the person to confirm something: one yes or no each.
//!
//! One file per block; this module only re-exports them, so an app writes
//! `confirm::value`, never `confirm::value::value`.

mod action;
mod data;
mod properties;
mod summary;
mod value;

pub use action::action;
pub use data::data;
pub use properties::properties;
pub use summary::summary;
pub use value::{Footer, ValueKind, value};
