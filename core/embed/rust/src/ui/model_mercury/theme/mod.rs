pub mod bootloader;

use crate::ui::{
    component::text::{LineBreaking, PageBreaking, TextStyle},
    display::{Color, Font, Icon},
    geometry::Insets,
};

use super::component::{ButtonStyle, ButtonStyleSheet, LoaderStyle, LoaderStyleSheet};

// Typical backlight values.
pub const BACKLIGHT_NORMAL: u16 = 150;
pub const BACKLIGHT_DIM: u16 = 5;

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

// TODO: delete colors below when ui-t3t1 done
pub const RED: Color = Color::rgb(0xE7, 0x0E, 0x0E); // button
pub const RED_DARK: Color = Color::rgb(0xAE, 0x09, 0x09); // button pressed
pub const YELLOW: Color = Color::rgb(0xD9, 0x9E, 0x00); // button
pub const YELLOW_DARK: Color = Color::rgb(0x7A, 0x58, 0x00); // button pressed
pub const GREEN_DARK: Color = Color::rgb(0x00, 0x55, 0x1D); // button pressed
pub const BLUE: Color = Color::rgb(0x06, 0x1E, 0xAD); // button
pub const BLUE_DARK: Color = Color::rgb(0x04, 0x10, 0x58); // button pressed
pub const OFF_WHITE: Color = Color::rgb(0xDE, 0xDE, 0xDE); // very light grey
pub const GREY_MEDIUM: Color = Color::rgb(0x4F, 0x4F, 0x4F); // button pressed
pub const VIOLET: Color = Color::rgb(0x95, 0x00, 0xCA);

pub const FATAL_ERROR_COLOR: Color = Color::rgb(0xE7, 0x0E, 0x0E);
pub const FATAL_ERROR_HIGHLIGHT_COLOR: Color = Color::rgb(0xFF, 0x41, 0x41);

// Commonly used corner radius (i.e. for buttons).
pub const RADIUS: u8 = 2;

// UI icons (greyscale).

// 20x20
include_icon!(
    ICON_BULLET_CHECKMARK,
    "model_mercury/res/bullet_checkmark20.toif"
);
include_icon!(ICON_PAGE_DOWN, "model_mercury/res/page_down20.toif");
include_icon!(ICON_PAGE_UP, "model_mercury/res/page_up20.toif");

// 24x24
include_icon!(ICON_CANCEL, "model_mercury/res/cancel24.toif");
include_icon!(ICON_CHEVRON_RIGHT, "model_mercury/res/chevron_right24.toif");
include_icon!(ICON_DOWNLOAD, "model_mercury/res/download24.toif");
include_icon!(
    ICON_EXCLAMATION_MARK,
    "model_mercury/res/exclamation_mark24.toif"
);
include_icon!(ICON_FIRE, "model_mercury/res/fire24.toif");
include_icon!(ICON_QR_CODE, "model_mercury/res/qr_code24.toif");
include_icon!(ICON_REBOOT, "model_mercury/res/reboot24.toif");

// 30x30
include_icon!(ICON_AUTOFILL, "model_mercury/res/autofill30.toif");
include_icon!(ICON_CLOSE, "model_mercury/res/close30.toif");
include_icon!(ICON_DELETE, "model_mercury/res/delete30.toif");
include_icon!(ICON_MENU, "model_mercury/res/menu30.toif");
include_icon!(
    ICON_SIMPLE_CHECKMARK,
    "model_mercury/res/simple_checkmark30.toif"
);

// 40x40
include_icon!(ICON_MINUS, "model_mercury/res/minus40.toif");
include_icon!(ICON_PLUS, "model_mercury/res/plus40.toif");

// TODO remove TT icons:

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
            border_color: BG,
            border_radius: 0,
            border_width: 1,
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
            border_color: BG,
            border_radius: 0,
            border_width: 1,
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

pub const TEXT_SUPER: TextStyle = TextStyle::new(Font::BIG, GREY_EXTRA_LIGHT, BG, GREY, GREY);
pub const TEXT_MAIN: TextStyle = TextStyle::new(Font::NORMAL, GREY_EXTRA_LIGHT, BG, GREY, GREY);
pub const TEXT_SUB: TextStyle = TextStyle::new(Font::SUB, GREY, BG, GREY, GREY);
pub const TEXT_MONO: TextStyle = TextStyle::new(Font::MONO, GREY_EXTRA_LIGHT, BG, GREY, GREY)
    .with_line_breaking(LineBreaking::BreakWordsNoHyphen)
    .with_page_breaking(PageBreaking::CutAndInsertEllipsisBoth)
    .with_ellipsis_icon(ICON_PAGE_NEXT, 0)
    .with_prev_page_icon(ICON_PAGE_PREV, 0);

// TODO: remove TextStyles below when ui-t3t1 done
pub const TEXT_NORMAL: TextStyle = TextStyle::new(Font::NORMAL, FG, BG, GREY_LIGHT, GREY_LIGHT);
pub const TEXT_DEMIBOLD: TextStyle = TextStyle::new(Font::DEMIBOLD, FG, BG, GREY_LIGHT, GREY_LIGHT);
pub const TEXT_BOLD: TextStyle = TextStyle::new(Font::BOLD, FG, BG, GREY_LIGHT, GREY_LIGHT);

/// Decide the text style of chunkified text according to its length.
pub fn get_chunkified_text_style(character_length: usize) -> &'static TextStyle {
    // Longer addresses have smaller x_offset so they fit even with scrollbar
    // (as they will be shown on more than one page)
    const FITS_ON_ONE_PAGE: usize = 16 * 4;
    if character_length <= FITS_ON_ONE_PAGE {
        &TEXT_MONO_ADDRESS_CHUNKS
    } else {
        &TEXT_MONO_ADDRESS_CHUNKS_SMALLER_X_OFFSET
    }
}

/// Convert Python-side numeric id to a `TextStyle`.
pub fn textstyle_number(num: i32) -> &'static TextStyle {
    let font = Font::from_i32(-num);
    match font {
        Some(Font::DEMIBOLD) => &TEXT_DEMIBOLD,
        Some(Font::BOLD) => &TEXT_BOLD,
        Some(Font::MONO) => &TEXT_MONO,
        _ => &TEXT_NORMAL,
    }
}

pub const TEXT_NORMAL_OFF_WHITE: TextStyle =
    TextStyle::new(Font::NORMAL, OFF_WHITE, BG, GREY_LIGHT, GREY_LIGHT);
pub const TEXT_CHECKLIST_DEFAULT: TextStyle =
    TextStyle::new(Font::NORMAL, GREY_LIGHT, BG, GREY_LIGHT, GREY_LIGHT);
pub const TEXT_CHECKLIST_SELECTED: TextStyle =
    TextStyle::new(Font::NORMAL, FG, BG, GREY_LIGHT, GREY_LIGHT);
pub const TEXT_CHECKLIST_DONE: TextStyle =
    TextStyle::new(Font::NORMAL, GREEN_DARK, BG, GREY_LIGHT, GREY_LIGHT);

pub const CONTENT_BORDER: i16 = 0;
pub const BUTTON_HEIGHT: i16 = 50;
pub const BUTTON_WIDTH: i16 = 56;
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
    Insets::new(0, 0, 0, 0)
}
