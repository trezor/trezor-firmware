pub mod bootloader;

use crate::{
    time::Duration,
    ui::{
        component::{
            text::{layout::Chunks, LineBreaking, PageBreaking, TextStyle},
            FixedHeightBar,
        },
        display::{Color, Font, Icon},
        geometry::{Insets, Offset},
    },
};

use super::component::{ButtonStyle, ButtonStyleSheet, LoaderStyle, LoaderStyleSheet, ResultStyle};

use num_traits::FromPrimitive;

pub const ERASE_HOLD_DURATION: Duration = Duration::from_millis(1500);

// Typical backlight values.
pub const BACKLIGHT_NORMAL: u16 = 150;
pub const BACKLIGHT_LOW: u16 = 45;
pub const BACKLIGHT_DIM: u16 = 5;
pub const BACKLIGHT_NONE: u16 = 2;
pub const BACKLIGHT_MAX: u16 = 255;

// Color palette.
pub const WHITE: Color = Color::rgb(0xFF, 0xFF, 0xFF);
pub const BLACK: Color = Color::rgb(0, 0, 0);
pub const FG: Color = WHITE; // Default foreground (text & icon) color.
pub const BG: Color = BLACK; // Default background color.
pub const RED: Color = Color::rgb(0xE7, 0x0E, 0x0E); // button
pub const RED_DARK: Color = Color::rgb(0xAE, 0x09, 0x09); // button pressed
pub const YELLOW: Color = Color::rgb(0xD9, 0x9E, 0x00); // button
pub const YELLOW_DARK: Color = Color::rgb(0x7A, 0x58, 0x00); // button pressed
pub const GREEN: Color = Color::rgb(0x00, 0xAA, 0x35); // button
pub const GREEN_DARK: Color = Color::rgb(0x00, 0x55, 0x1D); // button pressed
pub const BLUE: Color = Color::rgb(0x06, 0x1E, 0xAD); // button
pub const BLUE_DARK: Color = Color::rgb(0x04, 0x10, 0x58); // button pressed
pub const OFF_WHITE: Color = Color::rgb(0xDE, 0xDE, 0xDE); // very light grey
pub const GREY_LIGHT: Color = Color::rgb(0x90, 0x90, 0x90); // secondary text
pub const GREY_MEDIUM: Color = Color::rgb(0x4F, 0x4F, 0x4F); // button pressed
pub const GREY_DARK: Color = Color::rgb(0x35, 0x35, 0x35); // button
pub const VIOLET: Color = Color::rgb(0x95, 0x00, 0xCA);

pub const FATAL_ERROR_COLOR: Color = Color::rgb(0xE7, 0x0E, 0x0E);
pub const FATAL_ERROR_HIGHLIGHT_COLOR: Color = Color::rgb(0xFF, 0x41, 0x41);

// Commonly used corner radius (i.e. for buttons).
pub const RADIUS: u8 = 2;

// Full-size QR code.
pub const QR_SIDE_MAX: u32 = 140;

// UI icons (greyscale).
// Button icons.
include_icon!(ICON_CANCEL, "model_tt/res/x24.toif");
include_icon!(ICON_CONFIRM, "model_tt/res/check24.toif");
include_icon!(ICON_SPACE, "model_tt/res/space.toif");
include_icon!(ICON_BACK, "model_tt/res/caret-left24.toif");
include_icon!(ICON_FORWARD, "model_tt/res/caret-right24.toif");
include_icon!(ICON_UP, "model_tt/res/caret-up24.toif");
include_icon!(ICON_DOWN, "model_tt/res/caret-down24.toif");
include_icon!(ICON_CLICK, "model_tt/res/finger24.toif");

include_icon!(ICON_CORNER_CANCEL, "model_tt/res/x32.toif");
include_icon!(ICON_CORNER_INFO, "model_tt/res/info32.toif");

// Checklist symbols.
include_icon!(ICON_LIST_CURRENT, "model_tt/res/arrow-right16.toif");
include_icon!(ICON_LIST_CHECK, "model_tt/res/check16.toif");

// Homescreen notifications.
include_icon!(ICON_WARN, "model_tt/res/warning16.toif");
include_icon!(ICON_WARNING40, "model_tt/res/warning40.toif");
include_icon!(ICON_LOCK, "model_tt/res/lock16.toif");
include_icon!(ICON_LOCK_BIG, "model_tt/res/lock24.toif");
include_icon!(ICON_COINJOIN, "model_tt/res/coinjoin16.toif");
include_icon!(ICON_MAGIC, "model_tt/res/magic.toif");

// Text arrows.
include_icon!(ICON_PAGE_NEXT, "model_tt/res/page-next.toif");
include_icon!(ICON_PAGE_PREV, "model_tt/res/page-prev.toif");

// Large, three-color icons.
pub const WARN_COLOR: Color = YELLOW;
pub const INFO_COLOR: Color = BLUE;
pub const SUCCESS_COLOR: Color = GREEN;
pub const ERROR_COLOR: Color = RED;
include_icon!(IMAGE_FG_WARN, "model_tt/res/fg-warning48.toif");
include_icon!(IMAGE_FG_SUCCESS, "model_tt/res/fg-check48.toif");
include_icon!(IMAGE_FG_ERROR, "model_tt/res/fg-error48.toif");
include_icon!(IMAGE_FG_INFO, "model_tt/res/fg-info48.toif");
include_icon!(IMAGE_FG_USER, "model_tt/res/fg-user48.toif");
include_icon!(IMAGE_BG_CIRCLE, "model_tt/res/circle48.toif");
include_icon!(IMAGE_BG_OCTAGON, "model_tt/res/octagon48.toif");

// Non-square button backgrounds.
include_icon!(IMAGE_BG_BACK_BTN, "model_tt/res/bg-back40.toif");
include_icon!(IMAGE_BG_BACK_BTN_TALL, "model_tt/res/bg-back52.toif");

// Welcome screen.
include_icon!(ICON_LOGO, "model_tt/res/lock_full.toif");
include_icon!(ICON_LOGO_EMPTY, "model_tt/res/lock_empty.toif");

// Default homescreen
pub const IMAGE_HOMESCREEN: &[u8] = include_res!("model_tt/res/bg.jpg");

// Scrollbar/PIN dots.
include_icon!(DOT_ACTIVE, "model_tt/res/scroll-active.toif");
include_icon!(DOT_INACTIVE, "model_tt/res/scroll-inactive.toif");
include_icon!(DOT_INACTIVE_HALF, "model_tt/res/scroll-inactive-half.toif");
include_icon!(
    DOT_INACTIVE_QUARTER,
    "model_tt/res/scroll-inactive-quarter.toif"
);
include_icon!(DOT_SMALL, "model_tt/res/scroll-small.toif");

pub const fn label_default() -> TextStyle {
    TEXT_NORMAL
}

pub const fn label_keyboard() -> TextStyle {
    TextStyle::new(Font::DEMIBOLD, OFF_WHITE, BG, GREY_LIGHT, GREY_LIGHT)
}

pub const fn label_keyboard_prompt() -> TextStyle {
    TextStyle::new(Font::DEMIBOLD, GREY_LIGHT, BG, GREY_LIGHT, GREY_LIGHT)
}

pub const fn label_keyboard_warning() -> TextStyle {
    TextStyle::new(Font::DEMIBOLD, RED, BG, GREY_LIGHT, GREY_LIGHT)
}

pub const fn label_keyboard_minor() -> TextStyle {
    TEXT_NORMAL_OFF_WHITE
}

pub const fn label_warning() -> TextStyle {
    TEXT_DEMIBOLD
}

pub const fn label_warning_value() -> TextStyle {
    TEXT_NORMAL_OFF_WHITE
}

pub const fn label_recovery_title() -> TextStyle {
    TEXT_BOLD
}

pub const fn label_recovery_description() -> TextStyle {
    TEXT_NORMAL_OFF_WHITE
}

pub const fn label_progress() -> TextStyle {
    TEXT_BOLD
}

pub const fn label_title() -> TextStyle {
    TextStyle::new(Font::BOLD, GREY_LIGHT, BG, GREY_LIGHT, GREY_LIGHT)
}

pub const fn label_subtitle() -> TextStyle {
    TextStyle::new(Font::MONO, GREY_LIGHT, BG, GREY_LIGHT, GREY_LIGHT)
}

pub const fn label_coinjoin_progress() -> TextStyle {
    TextStyle::new(Font::BOLD, FG, YELLOW, FG, FG)
}

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
            button_color: GREY_MEDIUM,
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

pub const fn button_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::BOLD,
            text_color: FG,
            button_color: GREEN,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: Font::BOLD,
            text_color: FG,
            button_color: GREEN_DARK,
            background_color: BG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: Font::BOLD,
            text_color: GREY_LIGHT,
            button_color: GREEN_DARK,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
    }
}

pub const fn button_cancel() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::BOLD,
            text_color: FG,
            button_color: RED,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: Font::BOLD,
            text_color: FG,
            button_color: RED_DARK,
            background_color: BG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: Font::BOLD,
            text_color: GREY_LIGHT,
            button_color: RED,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
    }
}

pub const fn button_danger() -> ButtonStyleSheet {
    button_cancel()
}

pub const fn button_reset() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::BOLD,
            text_color: FG,
            button_color: YELLOW,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: Font::BOLD,
            text_color: FG,
            button_color: YELLOW_DARK,
            background_color: BG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: Font::BOLD,
            text_color: FG,
            button_color: YELLOW,
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
            border_color: GREY_MEDIUM,
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

pub const fn button_info() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::BOLD,
            text_color: FG,
            button_color: BLUE,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: Font::BOLD,
            text_color: FG,
            button_color: BLUE_DARK,
            background_color: BG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: Font::BOLD,
            text_color: GREY_LIGHT,
            button_color: BLUE,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
    }
}

pub const fn button_pin() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::MONO,
            text_color: FG,
            button_color: GREY_DARK,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: Font::MONO,
            text_color: FG,
            button_color: GREY_MEDIUM,
            background_color: BG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: Font::MONO,
            text_color: GREY_LIGHT,
            button_color: BG, // so there is no "button" itself, just the text
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
    }
}

pub const fn button_pin_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::MONO,
            text_color: FG,
            button_color: GREEN,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: Font::MONO,
            text_color: FG,
            button_color: GREEN_DARK,
            background_color: BG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: Font::MONO,
            text_color: GREY_LIGHT,
            button_color: GREY_DARK,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
    }
}

pub const fn button_pin_autocomplete() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::MONO,
            text_color: FG,
            button_color: GREY_DARK, // same as PIN buttons
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: Font::MONO,
            text_color: FG,
            button_color: GREEN_DARK,
            background_color: BG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: Font::MONO,
            text_color: GREY_LIGHT,
            button_color: BG,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
    }
}

pub const fn button_suggestion_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::MONO,
            text_color: GREEN_DARK,
            button_color: GREEN,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: Font::MONO,
            text_color: FG,
            button_color: GREEN_DARK,
            background_color: BG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: Font::MONO,
            text_color: GREY_LIGHT,
            button_color: GREY_DARK,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
    }
}

pub const fn button_suggestion_autocomplete() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::MONO,
            text_color: GREY_LIGHT,
            button_color: GREY_DARK, // same as PIN buttons
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: Font::MONO,
            text_color: FG,
            button_color: GREEN_DARK,
            background_color: BG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: Font::MONO,
            text_color: GREY_LIGHT,
            button_color: BG,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
    }
}

pub const fn button_counter() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::DEMIBOLD,
            text_color: FG,
            button_color: GREY_DARK,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: Font::DEMIBOLD,
            text_color: FG,
            button_color: GREY_MEDIUM,
            background_color: BG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: Font::DEMIBOLD,
            text_color: GREY_LIGHT,
            button_color: GREY_DARK,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
    }
}

pub const fn button_clear() -> ButtonStyleSheet {
    button_default()
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
/// Makes sure that the displayed text (usually address) will get divided into
/// smaller chunks.
pub const TEXT_MONO_ADDRESS_CHUNKS: TextStyle = TEXT_MONO
    .with_chunks(Chunks::new(4, 9))
    .with_line_spacing(5);
/// Smaller horizontal chunk offset, used e.g. for long Cardano addresses.
/// Also moving the next page ellipsis to the left (as there is a space on the
/// left). Last but not least, maximum number of rows is 4 in this case.
pub const TEXT_MONO_ADDRESS_CHUNKS_SMALLER_X_OFFSET: TextStyle = TEXT_MONO
    .with_chunks(Chunks::new(4, 7).with_max_rows(4))
    .with_line_spacing(5)
    .with_ellipsis_icon(ICON_PAGE_NEXT, -12);

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
pub const KEYBOARD_SPACING: i16 = BUTTON_SPACING;
pub const CHECKLIST_SPACING: i16 = 10;
pub const RECOVERY_SPACING: i16 = 18;
pub const CORNER_BUTTON_SIDE: i16 = 44;
pub const CORNER_BUTTON_SPACING: i16 = BUTTON_SPACING;
pub const INFO_BUTTON_HEIGHT: i16 = 44;
pub const PIN_BUTTON_HEIGHT: i16 = 40;
pub const MNEMONIC_BUTTON_HEIGHT: i16 = 52;
pub const RESULT_PADDING: i16 = 6;
pub const RESULT_FOOTER_START: i16 = 171;
pub const RESULT_FOOTER_HEIGHT: i16 = 62;

// checklist settings
pub const CHECKLIST_CHECK_WIDTH: i16 = 16;
pub const CHECKLIST_DONE_OFFSET: Offset = Offset::new(-2, 6);
pub const CHECKLIST_CURRENT_OFFSET: Offset = Offset::new(2, 3);

pub const fn button_bar<T>(inner: T) -> FixedHeightBar<T> {
    FixedHeightBar::bottom(inner, BUTTON_HEIGHT)
}

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

pub const fn borders_horizontal_scroll() -> Insets {
    Insets::new(6, 6, 0, 6)
}

pub const fn borders_notification() -> Insets {
    Insets::new(48, 6, 6, 6)
}

pub const RESULT_ERROR: ResultStyle =
    ResultStyle::new(FG, FATAL_ERROR_COLOR, FATAL_ERROR_HIGHLIGHT_COLOR);
