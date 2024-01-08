pub mod bootloader;

pub mod backlight;

use crate::ui::{
    component::text::{LineBreaking, PageBreaking, TextStyle},
    display::{Color, Font, Icon},
    geometry::Insets,
};

use super::component::{ButtonStyle, ButtonStyleSheet, LoaderStyle, LoaderStyleSheet};

// Color palette.
pub const WHITE: Color = Color::rgb(0xFF, 0xFF, 0xFF);
pub const BLACK: Color = Color::rgb(0, 0, 0);
pub const FG: Color = WHITE; // Default foreground (text & icon) color.
pub const BG: Color = BLACK; // Default background color.
pub const GREY_EXTRA_DARK: Color = Color::rgb(0x16, 0x1F, 0x24);
pub const GREY_DARK: Color = Color::rgb(0x46, 0x48, 0x4A);
pub const GREY: Color = Color::rgb(0x8B, 0x8F, 0x93); // secondary text, subtitle, instructions
pub const GREY_LIGHT: Color = Color::rgb(0xC7, 0xCD, 0xD3); // content
pub const GREY_EXTRA_LIGHT: Color = Color::rgb(0xF0, 0xF0, 0xF0); // primary text, header
pub const GREEN: Color = Color::rgb(0x08, 0x74, 0x48);
pub const GREEN_LIGHT: Color = Color::rgb(0x0B, 0xA5, 0x67);
pub const GREEN_LIME: Color = Color::rgb(0x9B, 0xE8, 0x87);
pub const ORANGE_DIMMED: Color = Color::rgb(0x9E, 0x57, 0x42);
pub const ORANGE_LIGHT: Color = Color::rgb(0xFF, 0x8D, 0x6A); // cancel button

pub const FATAL_ERROR_COLOR: Color = Color::rgb(0xE7, 0x0E, 0x0E);
pub const FATAL_ERROR_HIGHLIGHT_COLOR: Color = Color::rgb(0xFF, 0x41, 0x41);

// Commonly used corner radius (i.e. for buttons).
pub const RADIUS: u8 = 2;

// UI icons (greyscale).
// Button icons.
include_icon!(ICON_CANCEL, "model_mercury/res/x24.toif");
include_icon!(ICON_CONFIRM, "model_mercury/res/check24.toif");
include_icon!(ICON_UP, "model_mercury/res/caret-up24.toif");

include_icon!(ICON_CORNER_CANCEL, "model_mercury/res/x32.toif");
include_icon!(ICON_CORNER_INFO, "model_mercury/res/info32.toif");

// Checklist symbols.
include_icon!(ICON_LIST_CURRENT, "model_mercury/res/arrow-right16.toif");
include_icon!(ICON_LIST_CHECK, "model_mercury/res/check16.toif");

// Homescreen notifications.
include_icon!(ICON_WARNING40, "model_mercury/res/warning40.toif");
include_icon!(ICON_LOCK_BIG, "model_mercury/res/lock24.toif");

// Text arrows.
include_icon!(ICON_PAGE_NEXT, "model_mercury/res/page-next.toif");
include_icon!(ICON_PAGE_PREV, "model_mercury/res/page-prev.toif");

// Large, three-color icons.
pub const WARN_COLOR: Color = ORANGE_LIGHT;
pub const INFO_COLOR: Color = GREY_LIGHT;
pub const SUCCESS_COLOR: Color = GREEN;
pub const ERROR_COLOR: Color = ORANGE_DIMMED;
include_icon!(IMAGE_FG_SUCCESS, "model_mercury/res/fg-check48.toif");
include_icon!(IMAGE_BG_CIRCLE, "model_mercury/res/circle48.toif");

// Welcome screen.
include_icon!(ICON_LOGO, "model_mercury/res/lock_full.toif");

pub const fn button_default() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::BOLD,
            text_color: FG,
            button_color: GREY_DARK,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: Font::BOLD,
            text_color: FG,
            button_color: GREY,
            background_color: BG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: Font::BOLD,
            text_color: GREY_LIGHT,
            button_color: GREY_DARK,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
    }
}

pub const fn button_moreinfo() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::BOLD,
            text_color: FG,
            button_color: BG,
            background_color: BG,
            border_color: GREY_DARK,
            border_radius: RADIUS,
            border_width: 2,
        },
        active: &ButtonStyle {
            font: Font::BOLD,
            text_color: FG,
            button_color: BG,
            background_color: BG,
            border_color: GREY,
            border_radius: RADIUS,
            border_width: 2,
        },
        disabled: &ButtonStyle {
            font: Font::BOLD,
            text_color: GREY_LIGHT,
            button_color: BG,
            background_color: BG,
            border_color: GREY_DARK,
            border_radius: RADIUS,
            border_width: 2,
        },
    }
}

pub const fn loader_default() -> LoaderStyleSheet {
    LoaderStyleSheet {
        normal: &LoaderStyle {
            icon: None,
            loader_color: FG,
            background_color: BG,
        },
        active: &LoaderStyle {
            icon: None,
            loader_color: GREEN,
            background_color: BG,
        },
    }
}

pub const fn loader_lock_icon() -> LoaderStyleSheet {
    LoaderStyleSheet {
        normal: &LoaderStyle {
            icon: Some((ICON_LOCK_BIG, FG)),
            loader_color: FG,
            background_color: BG,
        },
        active: &LoaderStyle {
            icon: Some((ICON_LOCK_BIG, FG)),
            loader_color: GREEN,
            background_color: BG,
        },
    }
}

pub const TEXT_NORMAL: TextStyle = TextStyle::new(Font::NORMAL, FG, BG, GREY_LIGHT, GREY_LIGHT);
pub const TEXT_DEMIBOLD: TextStyle = TextStyle::new(Font::DEMIBOLD, FG, BG, GREY_LIGHT, GREY_LIGHT);
pub const TEXT_BOLD: TextStyle = TextStyle::new(Font::BOLD, FG, BG, GREY_LIGHT, GREY_LIGHT);
pub const TEXT_MONO: TextStyle = TextStyle::new(Font::MONO, FG, BG, GREY_LIGHT, GREY_LIGHT)
    .with_line_breaking(LineBreaking::BreakWordsNoHyphen)
    .with_page_breaking(PageBreaking::CutAndInsertEllipsisBoth)
    .with_ellipsis_icon(ICON_PAGE_NEXT, 0)
    .with_prev_page_icon(ICON_PAGE_PREV, 0);

pub const BUTTON_SPACING: i16 = 6;
pub const CORNER_BUTTON_SIDE: i16 = 44;
pub const RESULT_PADDING: i16 = 6;
pub const RESULT_FOOTER_START: i16 = 171;

/// +----------+
/// |     6    |
/// |  +----+  |
/// | 6|    | 6|
/// |  +----+  |
/// |     6    |
/// +----------+
pub const fn borders() -> Insets {
    Insets::new(6, 6, 6, 6)
}
