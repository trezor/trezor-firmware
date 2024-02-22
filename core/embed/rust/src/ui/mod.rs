#[macro_use]
pub mod macros;

pub mod animation;
pub mod canvas;
pub mod component;
pub mod constant;
pub mod display;
pub mod event;
pub mod geometry;
pub mod lerp;
pub mod screens;
pub mod shape;
#[macro_use]
pub mod util;

pub mod layout;

#[cfg(feature = "model_tr")]
pub mod model_tr;
#[cfg(feature = "model_tt")]
pub mod model_tt;

#[cfg(all(
    feature = "model_t1",
    not(feature = "model_tr"),
    not(feature = "model_tt")
))]
pub use model_t1 as model;
#[cfg(all(feature = "model_tr", not(feature = "model_tt")))]
pub use model_tr as model;
#[cfg(feature = "model_tt")]
pub use model_tt as model;
