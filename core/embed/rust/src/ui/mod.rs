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

#[cfg(feature = "layout_bolt")]
pub mod layout_bolt;
#[cfg(feature = "layout_caesar")]
pub mod layout_caesar;
#[cfg(feature = "layout_delizia")]
pub mod layout_delizia;

#[cfg(feature = "bootloader")]
pub mod ui_bootloader;

#[cfg(feature = "prodtest")]
pub mod ui_prodtest;

pub mod ui_common;
#[cfg(feature = "micropython")]
pub mod ui_firmware;

pub use ui_common::CommonUI;

#[cfg(feature = "ui_debug_overlay")]
pub use ui_common::DebugOverlay;

#[cfg(all(
    feature = "layout_delizia",
    not(feature = "layout_caesar"),
    not(feature = "layout_bolt")
))]
pub type ModelUI = crate::ui::layout_delizia::UIDelizia;

#[cfg(all(feature = "layout_caesar", not(feature = "layout_bolt")))]
pub type ModelUI = crate::ui::layout_caesar::UICaesar;

#[cfg(feature = "layout_bolt")]
pub type ModelUI = crate::ui::layout_bolt::UIBolt;
