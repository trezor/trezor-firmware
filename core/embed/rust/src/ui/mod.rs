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
#[cfg(feature = "layout_quicksilver")]
pub mod layout_quicksilver;
#[cfg(feature = "layout_samson")]
pub mod layout_samson;

#[cfg(feature = "bootloader")]
pub mod ui_bootloader;
pub mod ui_common;
#[cfg(feature = "micropython")]
pub mod ui_firmware;

pub use ui_common::CommonUI;

#[cfg(all(
    feature = "layout_quicksilver",
    not(feature = "layout_samson"),
    not(feature = "layout_bolt")
))]
pub type ModelUI = crate::ui::layout_quicksilver::UIQuicksilver;

#[cfg(all(feature = "layout_samson", not(feature = "layout_bolt")))]
pub type ModelUI = crate::ui::layout_samson::UISamson;

#[cfg(feature = "layout_bolt")]
pub type ModelUI = crate::ui::layout_bolt::UIBolt;
