use crate::{
    time::Duration,
    ui::{
        component::{
            text::{formatted::FormattedFonts, LineBreaking, PageBreaking, TextStyle},
            FixedHeightBar,
        },
        display::{Color, Font},
        geometry::Insets,
    },
};

use super::component::{ButtonStyle, ButtonStyleSheet, LoaderStyle, LoaderStyleSheet};

use crate::ui::display::toif::NamedToif;
use num_traits::FromPrimitive;

pub const ERASE_HOLD_DURATION: Duration = Duration::from_millis(1500);

// Typical backlight values.
pub const BACKLIGHT_NORMAL: i32 = 150;
pub const BACKLIGHT_LOW: i32 = 45;
pub const BACKLIGHT_DIM: i32 = 5;
pub const BACKLIGHT_NONE: i32 = 2;
pub const BACKLIGHT_MAX: i32 = 255;

// Color palette.
pub const WHITE: Color = Color::rgb(0xFF, 0xFF, 0xFF);
pub const BLACK: Color = Color::rgb(0, 0, 0);
pub const FG: Color = WHITE; // Default foreground (text & icon) color.
pub const BG: Color = BLACK; // Default background color.
pub const RED: Color = Color::rgb(0xCD, 0x49, 0x49); // dark-coral
pub const RED_DARK: Color = Color::rgb(0xA6, 0x2D, 0x2D);
pub const YELLOW: Color = Color::rgb(0xC1, 0x90, 0x09); // ochre
pub const YELLOW_DARK: Color = Color::rgb(0x9A, 0x73, 0x06); // FIXME
pub const GREEN: Color = Color::rgb(0x39, 0xA8, 0x14); // grass-green
pub const GREEN_DARK: Color = Color::rgb(0x10, 0xAB, 0x57);
pub const BLUE: Color = Color::rgb(0, 0x56, 0xBE); // blue
pub const BLUE_DARK: Color = Color::rgb(0, 0x44, 0x98); // FIXME
pub const OFF_WHITE: Color = Color::rgb(0xDE, 0xDE, 0xDE); // very light grey
pub const GREY_LIGHT: Color = Color::rgb(0xA8, 0xA8, 0xA8); // greyish
pub const GREY_MEDIUM: Color = Color::rgb(0x64, 0x64, 0x64);
pub const GREY_DARK: Color = Color::rgb(0x33, 0x33, 0x33); // greyer
pub const VIOLET: Color = Color::rgb(0x9E, 0x27, 0xD6);

// Commonly used corner radius (i.e. for buttons).
pub const RADIUS: u8 = 2;

// Full-size QR code.
pub const QR_SIDE_MAX: u32 = 140;

// Size of icons in the UI (i.e. inside buttons).
pub const ICON_SIZE: i16 = 16;

// UI icons (greyscale).
pub const ICON_CANCEL: NamedToif = NamedToif(include_res!("model_tt/res/cancel.toif"), "cancel");
pub const ICON_CONFIRM: NamedToif = NamedToif(include_res!("model_tt/res/confirm.toif"), "confirm");
pub const ICON_SPACE: NamedToif = NamedToif(include_res!("model_tt/res/space.toif"), "space");
pub const ICON_BACK: NamedToif = NamedToif(include_res!("model_tt/res/back.toif"), "back");
pub const ICON_CLICK: NamedToif = NamedToif(include_res!("model_tt/res/click.toif"), "click");
pub const ICON_NEXT: NamedToif = NamedToif(include_res!("model_tt/res/next.toif"), "next");
pub const ICON_WARN: NamedToif = NamedToif(include_res!("model_tt/res/warn-icon.toif"), "warn");
pub const ICON_MAGIC: NamedToif = NamedToif(include_res!("model_tt/res/magic.toif"), "magic");
pub const ICON_LIST_CURRENT: NamedToif =
    NamedToif(include_res!("model_tt/res/current.toif"), "current");
pub const ICON_LIST_CHECK: NamedToif = NamedToif(include_res!("model_tt/res/check.toif"), "check");
pub const ICON_LOCK: NamedToif = NamedToif(include_res!("model_tt/res/lock.toif"), "lock");

// Large, three-color icons.
pub const WARN_COLOR: Color = YELLOW;
pub const INFO_COLOR: Color = BLUE;
pub const SUCCESS_COLOR: Color = GREEN;
pub const ERROR_COLOR: Color = RED;
pub const IMAGE_FG_WARN: NamedToif =
    NamedToif(include_res!("model_tt/res/warn_fg.toif"), "warn_fg");
pub const IMAGE_FG_SUCCESS: NamedToif =
    NamedToif(include_res!("model_tt/res/success_fg.toif"), "success_fg");
pub const IMAGE_FG_ERROR: NamedToif =
    NamedToif(include_res!("model_tt/res/error_fg.toif"), "error_fg");
pub const IMAGE_FG_INFO: NamedToif =
    NamedToif(include_res!("model_tt/res/info_fg.toif"), "info_fg");
pub const IMAGE_BG_CIRCLE: NamedToif =
    NamedToif(include_res!("model_tt/res/circle.toif"), "circle");
pub const IMAGE_BG_TRIANGLE: NamedToif =
    NamedToif(include_res!("model_tt/res/triangle.toif"), "triangle");
pub const IMAGE_BG_BACK_BTN: NamedToif =
    NamedToif(include_res!("model_tt/res/back_btn.toif"), "back_btn");
pub const IMAGE_BG_BACK_BTN_TALL: NamedToif = NamedToif(
    include_res!("model_tt/res/back_btn_tall.toif"),
    "back_btn_tall",
);

// Default homescreen
pub const IMAGE_HOMESCREEN: &[u8] = include_res!("model_tt/res/bg.jpg");

// Scrollbar/PIN dots.
pub const DOT_ACTIVE: NamedToif = NamedToif(
    include_res!("model_tt/res/scroll-active.toif"),
    "scroll-active",
);
pub const DOT_INACTIVE: NamedToif = NamedToif(
    include_res!("model_tt/res/scroll-inactive.toif"),
    "scroll-inactive",
);
pub const DOT_INACTIVE_HALF: NamedToif = NamedToif(
    include_res!("model_tt/res/scroll-inactive-half.toif"),
    "scroll-inactive-half",
);
pub const DOT_INACTIVE_QUARTER: NamedToif = NamedToif(
    include_res!("model_tt/res/scroll-inactive-quarter.toif"),
    "scroll-inactive-quarter",
);
pub const DOT_SMALL: NamedToif = NamedToif(
    include_res!("model_tt/res/scroll-small.toif"),
    "scroll-small",
);

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

pub fn button_default() -> ButtonStyleSheet {
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

pub fn button_confirm() -> ButtonStyleSheet {
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

pub fn button_cancel() -> ButtonStyleSheet {
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

pub fn button_danger() -> ButtonStyleSheet {
    button_cancel()
}

pub fn button_reset() -> ButtonStyleSheet {
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

pub fn button_info() -> ButtonStyleSheet {
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

pub fn button_pin() -> ButtonStyleSheet {
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

pub fn button_counter() -> ButtonStyleSheet {
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

pub fn button_clear() -> ButtonStyleSheet {
    button_default()
}

pub fn loader_default() -> LoaderStyleSheet {
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
    .with_page_breaking(PageBreaking::Cut);

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

pub const fn borders_notification() -> Insets {
    Insets::new(48, 10, 14, 10)
}
