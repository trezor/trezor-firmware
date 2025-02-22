pub mod backlight;
#[cfg(feature = "bootloader")]
pub mod bootloader;
#[cfg(feature = "micropython")]
pub mod firmware;
#[cfg(feature = "micropython")]
pub use firmware::*;

use crate::ui::{display::Color, util::include_icon};

use super::{
    component::{ButtonStyle, ButtonStyleSheet, ResultStyle},
    fonts,
};

// Color palette.
pub const WHITE: Color = Color::rgb(0xFF, 0xFF, 0xFF);
pub const BLACK: Color = Color::rgb(0, 0, 0);
pub const FG: Color = WHITE; // Default foreground (text & icon) color.
pub const BG: Color = BLACK; // Default background color.
pub const GREY_EXTRA_LIGHT: Color = Color::rgb(0xF0, 0xF0, 0xF0);
pub const GREY_LIGHT: Color = Color::rgb(0xC7, 0xCD, 0xD3);
pub const GREY: Color = Color::rgb(0x8B, 0x8F, 0x93);
pub const GREY_DARK: Color = Color::rgb(0x46, 0x48, 0x4A);
pub const GREY_EXTRA_DARK: Color = Color::rgb(0x16, 0x1F, 0x24);
pub const GREY_SUPER_DARK: Color = Color::rgb(0x0B, 0x10, 0x12);

pub const GREEN_LIME: Color = Color::rgb(0x9B, 0xE8, 0x87);
pub const GREEN_LIGHT: Color = Color::rgb(0x0B, 0xA5, 0x67);
pub const GREEN: Color = Color::rgb(0x08, 0x74, 0x48);
pub const GREEN_DARK: Color = Color::rgb(0x06, 0x1E, 0x19);
pub const GREEN_EXTRA_DARK: Color = Color::rgb(0x03, 0x10, 0x0C);

pub const ORANGE: Color = Color::rgb(0xFF, 0x63, 0x30);
pub const ORANGE_DIMMED: Color = Color::rgb(0x9E, 0x57, 0x42);
pub const ORANGE_DARK: Color = Color::rgb(0x18, 0x0C, 0x0A);
pub const ORANGE_EXTRA_DARK: Color = Color::rgb(0x12, 0x07, 0x04);

pub const YELLOW: Color = Color::rgb(0xFF, 0xE4, 0x58);

pub const RED: Color = Color::rgb(0xFF, 0x30, 0x30);
pub const FATAL_ERROR_COLOR: Color = Color::rgb(0xE7, 0x0E, 0x0E);
pub const FATAL_ERROR_HIGHLIGHT_COLOR: Color = Color::rgb(0xFF, 0x41, 0x41);

// UI icons (white color).
include_icon!(ICON_CHEVRON_DOWN, "layout_eckhart/res/chevron_down.toif");
include_icon!(
    ICON_CHEVRON_DOWN_MINI,
    "layout_eckhart/res/chevron_down_mini.toif"
);
include_icon!(ICON_CHEVRON_LEFT, "layout_eckhart/res/chevron_left.toif");
include_icon!(ICON_CHEVRON_RIGHT, "layout_eckhart/res/chevron_right.toif");
include_icon!(ICON_CHEVRON_UP, "layout_eckhart/res/chevron_up.toif");
include_icon!(ICON_CLOSE, "layout_eckhart/res/close.toif");
include_icon!(ICON_DONE, "layout_eckhart/res/done.toif");
include_icon!(ICON_FORESLASH, "layout_eckhart/res/foreslash.toif");
include_icon!(ICON_INFO, "layout_eckhart/res/info.toif");
include_icon!(ICON_MENU, "layout_eckhart/res/menu.toif");
include_icon!(ICON_WARNING, "layout_eckhart/res/warning.toif");
// Keyboard icons
include_icon!(ICON_ASTERISK, "layout_eckhart/res/keyboard/asterisk.toif");
include_icon!(ICON_CHECKMARK, "layout_eckhart/res/keyboard/checkmark.toif");
include_icon!(ICON_CROSS, "layout_eckhart/res/keyboard/cross.toif");
include_icon!(
    ICON_DASH_HORIZONTAL,
    "layout_eckhart/res/keyboard/dash_horizontal.toif"
);
include_icon!(
    ICON_DASH_VERTICAL,
    "layout_eckhart/res/keyboard/dash_vertical.toif"
);
include_icon!(ICON_DELETE, "layout_eckhart/res/keyboard/delete.toif");
include_icon!(ICON_SPACE, "layout_eckhart/res/keyboard/space.toif");
include_icon!(
    ICON_SPECIAL_CHARS,
    "layout_eckhart/res/keyboard/special_chars_group.toif"
);
// Welcome screen.
include_icon!(ICON_LOGO, "layout_eckhart/res/lock_full.toif");
// Homescreen notifications.
include_icon!(ICON_WARNING40, "layout_eckhart/res/warning40.toif");

// Battery icons
include_icon!(ICON_BATTERY_BAR, "layout_eckhart/res/battery_bar.toif");
include_icon!(ICON_BATTERY_ZAP, "layout_eckhart/res/battery_zap.toif");

// Border overlay icons for bootloader screens and hold to confirm animation
include_icon!(ICON_BORDER_BL, "layout_eckhart/res/border/BL.toif");
include_icon!(ICON_BORDER_BR, "layout_eckhart/res/border/BR.toif");
include_icon!(ICON_BORDER_TL, "layout_eckhart/res/border/TL.toif");
include_icon!(ICON_BORDER_TR, "layout_eckhart/res/border/TR.toif");

// Icons for number input screen
include_icon!(ICON_PLUS, "layout_eckhart/res/plus.toif");
include_icon!(ICON_MINUS, "layout_eckhart/res/minus.toif");

pub const fn button_default() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: BG,
            icon_color: GREY_LIGHT,
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

// Result constants
pub const RESULT_PADDING: i16 = 6;
pub const RESULT_FOOTER_START: i16 = 171;
pub const RESULT_FOOTER_HEIGHT: i16 = 62;
pub const RESULT_ERROR: ResultStyle =
    ResultStyle::new(FG, FATAL_ERROR_COLOR, FATAL_ERROR_HIGHLIGHT_COLOR);
