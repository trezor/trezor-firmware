use crate::{
    time::Duration,
    ui::{
        component::{
            text::{formatted::FormattedFonts, LineBreaking, PageBreaking, TextStyle},
            FixedHeightBar,
        },
        display::{Color, Font, Icon},
        geometry::Insets,
    },
};

use super::component::{ButtonStyle, ButtonStyleSheet, LoaderStyle, LoaderStyleSheet};

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
pub const GREEN: Color = Color::rgb(0x00, 0xA7, 0x25); // button
pub const GREEN_DARK: Color = Color::rgb(0x00, 0x55, 0x1D); // button pressed
pub const BLUE: Color = Color::rgb(0x06, 0x1E, 0xAD); // button
pub const BLUE_DARK: Color = Color::rgb(0x04, 0x10, 0x58); // button pressed
pub const OFF_WHITE: Color = Color::rgb(0xDE, 0xDE, 0xDE); // very light grey
pub const GREY_LIGHT: Color = Color::rgb(0x90, 0x90, 0x90); // secondary text
pub const GREY_MEDIUM: Color = Color::rgb(0x4F, 0x4F, 0x4F); // button pressed
pub const GREY_DARK: Color = Color::rgb(0x28, 0x28, 0x28); // button
pub const VIOLET: Color = Color::rgb(0x95, 0x00, 0xCA);

pub const FATAL_ERROR_COLOR: Color = Color::rgb(0xAD, 0x2B, 0x2B);

// Commonly used corner radius (i.e. for buttons).
pub const RADIUS: u8 = 2;

// Full-size QR code.
pub const QR_SIDE_MAX: u32 = 140;

// Size of icons in the UI (i.e. inside buttons).
pub const ICON_SIZE: i16 = 16;

// UI icons (greyscale).
pub const ICON_CANCEL: &[u8] = include_res!("model_tt/res/cancel.toif");
pub const ICON_CANCEL_LARGER: &[u8] = include_res!("model_tt/res/cancel-larger.toif");
pub const ICON_CONFIRM: &[u8] = include_res!("model_tt/res/confirm.toif");
pub const ICON_SPACE: &[u8] = include_res!("model_tt/res/space.toif");
pub const ICON_BACK: &[u8] = include_res!("model_tt/res/back.toif");
pub const ICON_CLICK: &[u8] = include_res!("model_tt/res/click.toif");
pub const ICON_NEXT: &[u8] = include_res!("model_tt/res/next.toif");
pub const ICON_WARN: &[u8] = include_res!("model_tt/res/warn-icon.toif");
pub const ICON_MAGIC: &[u8] = include_res!("model_tt/res/magic.toif");
pub const ICON_LIST_CURRENT: &[u8] = include_res!("model_tt/res/current.toif");
pub const ICON_LIST_CHECK: &[u8] = include_res!("model_tt/res/check.toif");
pub const ICON_LOCK: &[u8] = include_res!("model_tt/res/lock.toif");
pub const ICON_LOGO: &[u8] = include_res!("model_tt/res/logo.toif");
pub const ICON_SUCCESS_SMALL: &[u8] = include_res!("model_tt/res/success_bld.toif");
pub const ICON_WARN_SMALL: &[u8] = include_res!("model_tt/res/warn_bld.toif");
pub const ICON_PAGE_NEXT: &[u8] = include_res!("model_tt/res/page-next.toif");
pub const ICON_PAGE_PREV: &[u8] = include_res!("model_tt/res/page-prev.toif");
pub const ICON_OCTA: &[u8] = include_res!("model_tt/res/octa-bang.toif");
pub const ICON_INFO_CIRCLE: &[u8] = include_res!("model_tt/res/info-circle.toif");

// Large, three-color icons.
pub const WARN_COLOR: Color = YELLOW;
pub const INFO_COLOR: Color = BLUE;
pub const SUCCESS_COLOR: Color = GREEN;
pub const ERROR_COLOR: Color = RED;
pub const IMAGE_FG_WARN: &[u8] = include_res!("model_tt/res/warn_fg.toif");
pub const IMAGE_FG_SUCCESS: &[u8] = include_res!("model_tt/res/success_fg.toif");
pub const IMAGE_FG_ERROR: &[u8] = include_res!("model_tt/res/error_fg.toif");
pub const IMAGE_FG_INFO: &[u8] = include_res!("model_tt/res/info_fg.toif");
pub const IMAGE_BG_CIRCLE: &[u8] = include_res!("model_tt/res/circle.toif");
pub const IMAGE_BG_TRIANGLE: &[u8] = include_res!("model_tt/res/triangle.toif");
pub const IMAGE_BG_BACK_BTN: &[u8] = include_res!("model_tt/res/back_btn.toif");
pub const IMAGE_BG_BACK_BTN_TALL: &[u8] = include_res!("model_tt/res/back_btn_tall.toif");

// Default homescreen
pub const IMAGE_HOMESCREEN: &[u8] = include_res!("model_tt/res/bg.jpg");

// Scrollbar/PIN dots.
pub const DOT_ACTIVE: &[u8] = include_res!("model_tt/res/scroll-active.toif");
pub const DOT_INACTIVE: &[u8] = include_res!("model_tt/res/scroll-inactive.toif");
pub const DOT_INACTIVE_HALF: &[u8] = include_res!("model_tt/res/scroll-inactive-half.toif");
pub const DOT_INACTIVE_QUARTER: &[u8] = include_res!("model_tt/res/scroll-inactive-quarter.toif");
pub const DOT_SMALL: &[u8] = include_res!("model_tt/res/scroll-small.toif");

pub const fn label_default() -> TextStyle {
    TEXT_NORMAL
}

pub const fn label_keyboard() -> TextStyle {
    TextStyle::new(Font::DEMIBOLD, OFF_WHITE, BG, GREY_LIGHT, GREY_LIGHT)
}

pub const fn label_keyboard_warning() -> TextStyle {
    TextStyle::new(Font::DEMIBOLD, RED, BG, GREY_LIGHT, GREY_LIGHT)
}

pub const fn label_keyboard_minor() -> TextStyle {
    TEXT_NORMAL_OFF_WHITE
}

pub const fn label_page_hint() -> TextStyle {
    TextStyle::new(Font::BOLD, GREY_LIGHT, BG, GREY_LIGHT, GREY_LIGHT)
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
            text_color: FG,
            button_color: GREEN,
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
            button_color: GREY_DARK,
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

pub const TEXT_NORMAL: TextStyle = TextStyle::new(Font::NORMAL, FG, BG, GREY_LIGHT, GREY_LIGHT);
pub const TEXT_DEMIBOLD: TextStyle = TextStyle::new(Font::DEMIBOLD, FG, BG, GREY_LIGHT, GREY_LIGHT);
pub const TEXT_BOLD: TextStyle = TextStyle::new(Font::BOLD, FG, BG, GREY_LIGHT, GREY_LIGHT);
pub const TEXT_MONO: TextStyle = TextStyle::new(Font::MONO, FG, BG, GREY_LIGHT, GREY_LIGHT)
    .with_line_breaking(LineBreaking::BreakWordsNoHyphen)
    .with_page_breaking(PageBreaking::CutAndInsertEllipsisBoth)
    .with_ellipsis_icon(Icon::new(ICON_PAGE_NEXT))
    .with_prev_page_icon(Icon::new(ICON_PAGE_PREV));

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
pub const TEXT_ERROR_NORMAL: TextStyle =
    TextStyle::new(Font::NORMAL, FG, FATAL_ERROR_COLOR, GREY_LIGHT, GREY_LIGHT);
pub const TEXT_ERROR_BOLD: TextStyle =
    TextStyle::new(Font::BOLD, FG, FATAL_ERROR_COLOR, GREY_LIGHT, GREY_LIGHT);

pub const TEXT_NORMAL_OFF_WHITE: TextStyle =
    TextStyle::new(Font::NORMAL, OFF_WHITE, BG, GREY_LIGHT, GREY_LIGHT);
pub const TEXT_CHECKLIST_DEFAULT: TextStyle =
    TextStyle::new(Font::NORMAL, GREY_LIGHT, BG, GREY_LIGHT, GREY_LIGHT);
pub const TEXT_CHECKLIST_SELECTED: TextStyle =
    TextStyle::new(Font::NORMAL, FG, BG, GREY_LIGHT, GREY_LIGHT);
pub const TEXT_CHECKLIST_DONE: TextStyle =
    TextStyle::new(Font::NORMAL, GREEN_DARK, BG, GREY_LIGHT, GREY_LIGHT);
pub const TEXT_XPUB: TextStyle = TEXT_NORMAL.with_line_breaking(LineBreaking::BreakWordsNoHyphen);

pub const FORMATTED: FormattedFonts = FormattedFonts {
    normal: Font::NORMAL,
    demibold: Font::DEMIBOLD,
    bold: Font::BOLD,
    mono: Font::MONO,
};

pub const CONTENT_BORDER: i16 = 5;
pub const KEYBOARD_SPACING: i16 = 8;
pub const BUTTON_HEIGHT: i16 = 38;
pub const BUTTON_SPACING: i16 = 6;
pub const CHECKLIST_SPACING: i16 = 10;
pub const RECOVERY_SPACING: i16 = 18;
pub const CORNER_BUTTON_SIDE: i16 = 32;
pub const CORNER_BUTTON_SPACING: i16 = 8;

/// Standard button height in pixels.
pub const fn button_rows(count: usize) -> i16 {
    let count = count as i16;
    BUTTON_HEIGHT * count + BUTTON_SPACING * count.saturating_sub(1)
}

pub const fn button_bar_rows<T>(rows: usize, inner: T) -> FixedHeightBar<T> {
    FixedHeightBar::bottom(inner, button_rows(rows))
}

pub const fn button_bar<T>(inner: T) -> FixedHeightBar<T> {
    button_bar_rows(1, inner)
}

/// +----------+
/// |    13    |
/// |  +----+  |
/// |10|    |10|
/// |  +----+  |
/// |    14    |
/// +----------+
pub const fn borders() -> Insets {
    Insets::new(13, 10, 14, 10)
}

pub const fn borders_scroll() -> Insets {
    Insets::new(13, 5, 14, 10)
}

pub const fn borders_horizontal_scroll() -> Insets {
    Insets::new(13, 10, 0, 10)
}

pub const fn borders_notification() -> Insets {
    Insets::new(48, 10, 14, 10)
}
