use crate::ui::{
    component::{
        label::LabelStyle,
        text::{formatted::FormattedFonts, TextStyle},
        FixedHeightBar,
    },
    display::{Color, Font},
    geometry::Insets,
};

use super::component::{ButtonStyle, ButtonStyleSheet, LoaderStyle, LoaderStyleSheet};

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

// Commonly used corner radius (i.e. for buttons).
pub const RADIUS: u8 = 2;

// Full-size QR code.
pub const QR_SIDE_MAX: u32 = 140;

// Size of icons in the UI (i.e. inside buttons).
pub const ICON_SIZE: i16 = 16;

// UI icons (greyscale).
pub const ICON_CANCEL: &[u8] = include_res!("model_tt/res/cancel.toif");
pub const ICON_CONFIRM: &[u8] = include_res!("model_tt/res/confirm.toif");
pub const ICON_SPACE: &[u8] = include_res!("model_tt/res/space.toif");
pub const ICON_BACK: &[u8] = include_res!("model_tt/res/back.toif");
pub const ICON_CLICK: &[u8] = include_res!("model_tt/res/click.toif");
pub const ICON_NEXT: &[u8] = include_res!("model_tt/res/next.toif");
pub const ICON_WARN: &[u8] = include_res!("model_tt/res/warn-icon.toif");
pub const ICON_LIST_CURRENT: &[u8] = include_res!("model_tt/res/current.toif");
pub const ICON_LIST_CHECK: &[u8] = include_res!("model_tt/res/check.toif");

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

// Scrollbar/PIN dots.
pub const DOT_ACTIVE: &[u8] = include_res!("model_tt/res/scroll-active.toif");
pub const DOT_INACTIVE: &[u8] = include_res!("model_tt/res/scroll-inactive.toif");
pub const DOT_SMALL: &[u8] = include_res!("model_tt/res/scroll-small.toif");

pub fn label_default() -> LabelStyle {
    LabelStyle {
        font: Font::NORMAL,
        text_color: FG,
        background_color: BG,
    }
}

pub fn label_keyboard() -> LabelStyle {
    LabelStyle {
        font: Font::DEMIBOLD,
        text_color: OFF_WHITE,
        background_color: BG,
    }
}

pub fn label_keyboard_warning() -> LabelStyle {
    LabelStyle {
        font: Font::DEMIBOLD,
        text_color: RED,
        background_color: BG,
    }
}

pub fn label_keyboard_minor() -> LabelStyle {
    LabelStyle {
        font: Font::NORMAL,
        text_color: OFF_WHITE,
        background_color: BG,
    }
}

pub fn label_page_hint() -> LabelStyle {
    LabelStyle {
        font: Font::BOLD,
        text_color: GREY_LIGHT,
        background_color: BG,
    }
}

pub fn label_warning() -> LabelStyle {
    LabelStyle {
        font: Font::DEMIBOLD,
        text_color: FG,
        background_color: BG,
    }
}

pub fn label_warning_value() -> LabelStyle {
    LabelStyle {
        font: Font::NORMAL,
        text_color: OFF_WHITE,
        background_color: BG,
    }
}

pub fn label_recovery_title() -> LabelStyle {
    LabelStyle {
        font: Font::BOLD,
        text_color: FG,
        background_color: BG,
    }
}

pub fn label_recovery_description() -> LabelStyle {
    LabelStyle {
        font: Font::NORMAL,
        text_color: OFF_WHITE,
        background_color: BG,
    }
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
            text_color: GREY_LIGHT,
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
pub const TEXT_MONO: TextStyle = TextStyle::new(Font::MONO, FG, BG, GREY_LIGHT, GREY_LIGHT);

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
    Insets::new(6, 10, 14, 10)
}
