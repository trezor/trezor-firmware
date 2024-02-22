#[cfg(feature = "model_tr")]
pub mod model_tr;
#[cfg(feature = "model_tr")]
pub use model_tr::render_on_display;

#[cfg(feature = "model_tt")]
pub mod model_tt;
#[cfg(feature = "model_tt")]
pub use model_tt::render_on_display;
