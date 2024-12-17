pub mod animation;
#[cfg(feature = "micropython")]
pub mod backlight;
pub mod button_request;
pub mod component;
pub mod constant;
pub mod display;
pub mod event;
#[cfg(all(feature = "micropython", feature = "touch"))]
pub mod flow;
pub mod geometry;
pub mod lerp;
pub mod shape;
pub mod util;

pub mod layout;

mod api;

#[cfg(feature = "model_mercury")]
pub mod model_mercury;
#[cfg(feature = "model_tr")]
pub mod model_tr;
#[cfg(feature = "model_tt")]
pub mod model_tt;

#[cfg(feature = "bootloader")]
pub mod ui_bootloader;
pub mod ui_common;
#[cfg(feature = "micropython")]
pub mod ui_firmware;

pub use ui_common::CommonUI;

#[cfg(all(
    feature = "model_mercury",
    not(feature = "model_tr"),
    not(feature = "model_tt")
))]
pub type ModelUI = crate::ui::model_mercury::UIMercury;

#[cfg(all(feature = "model_tr", not(feature = "model_tt")))]
pub type ModelUI = crate::ui::model_tr::UIModelTR;

#[cfg(feature = "model_tt")]
pub type ModelUI = crate::ui::model_tt::UIModelTT;
