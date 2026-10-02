//! Blocks that ask the person to confirm something: one yes or no each.
//!
//! One file per block; this module only re-exports them, so an app writes
//! `confirm::value`, never `confirm::value::value`.

mod action;
mod data;
mod properties;
mod summary;
mod value;

pub use action::{Action, action};
pub use data::{Data, data};
pub use properties::{Properties, properties};
pub use summary::{Summary, summary};
pub use value::{Footer, Value, ValueKind, value};
