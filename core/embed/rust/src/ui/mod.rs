#[macro_use]
pub mod macros;

pub mod animation;
pub mod component;
pub mod constant;
pub mod display;
pub mod event;
pub mod geometry;
pub mod lerp;
mod util;

#[cfg(feature = "micropython")]
pub mod layout;

#[cfg(feature = "model_t1")]
pub mod model_t1;
#[cfg(feature = "model_t1")]
pub use model_t1::component::*;
#[cfg(feature = "model_tr")]
pub mod model_tr;
#[cfg(feature = "model_tr")]
pub use model_tr::component::*;
#[cfg(feature = "model_tt")]
pub mod model_tt;
#[cfg(feature = "model_tt")]
pub use model_tt::component::*;

pub mod workflow;
