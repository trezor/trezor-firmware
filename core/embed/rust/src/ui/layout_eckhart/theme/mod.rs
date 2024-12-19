pub mod bootloader;

pub mod backlight;

use crate::{
    time::Duration,
    ui::{display::{Color, Font}, util::include_icon},
};

use super::component::{ButtonStyle, ButtonStyleSheet, ResultStyle};

pub const ERASE_HOLD_DURATION: Duration = Duration::from_millis(1500);

// Color palette.
// TODO: colors
pub const WHITE: Color = Color::rgb(0xFF, 0xFF, 0xFF);
pub const BLACK: Color = Color::rgb(0, 0, 0);
pub const FG: Color = WHITE; // Default foreground (text & icon) color.
pub const BG: Color = BLACK; // Default background color.
pub const GREY_DARK: Color = Color::rgb(0x46, 0x48, 0x4A);
pub const GREY_LIGHT: Color = Color::rgb(0xC7, 0xCD, 0xD3);

pub const FATAL_ERROR_COLOR: Color = Color::rgb(0xE7, 0x0E, 0x0E);
pub const FATAL_ERROR_HIGHLIGHT_COLOR: Color = Color::rgb(0xFF, 0x41, 0x41);

// UI icons (white color).
// TODO: icons

// Welcome screen.
include_icon!(ICON_LOGO, "layout_jefferson/res/lock_full.toif");

// Homescreen notifications.
include_icon!(ICON_WARNING40, "model_jefferson/res/warning40.toif");

// TODO: button styles
pub const fn button_default() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: BG,
            icon_color: FG,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_LIGHT,
            background_color: BG,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: GREY_DARK,
            icon_color: GREY_LIGHT,
            background_color: GREY_DARK,
        },
    }
}


pub const RESULT_PADDING: i16 = 6;
pub const RESULT_FOOTER_START: i16 = 171;
pub const RESULT_FOOTER_HEIGHT: i16 = 62;
pub const RESULT_ERROR: ResultStyle =
    ResultStyle::new(FG, FATAL_ERROR_COLOR, FATAL_ERROR_HIGHLIGHT_COLOR);
