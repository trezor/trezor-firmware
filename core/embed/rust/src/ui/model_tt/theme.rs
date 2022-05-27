use crate::ui::{
    component::{label::LabelStyle, text::layout::DefaultTextTheme},
    display::{Color, Font},
    geometry::Insets,
};

use super::component::{ButtonStyle, ButtonStyleSheet, LoaderStyle, LoaderStyleSheet};

// Font constants.
pub const FONT_NORMAL: Font = Font::new(-1);
pub const FONT_MEDIUM: Font = Font::new(-5);
pub const FONT_BOLD: Font = Font::new(-2);
pub const FONT_MONO: Font = Font::new(-3);

// Typical backlight values.
pub const BACKLIGHT_NORMAL: i32 = 150;
pub const BACKLIGHT_LOW: i32 = 45;
pub const BACKLIGHT_DIM: i32 = 5;
pub const BACKLIGHT_NONE: i32 = 2;
pub const BACKLIGHT_MAX: i32 = 255;

// Color palette.
pub const WHITE: Color = Color::rgb(255, 255, 255);
pub const BLACK: Color = Color::rgb(0, 0, 0);
pub const FG: Color = WHITE; // Default foreground (text & icon) color.
pub const BG: Color = BLACK; // Default background color.
pub const RED: Color = Color::rgb(205, 73, 73); // dark-coral
pub const RED_DARK: Color = Color::rgb(166, 45, 45);
pub const YELLOW: Color = Color::rgb(193, 144, 9); // ochre
pub const YELLOW_DARK: Color = Color::rgb(154, 115, 6); // FIXME
pub const GREEN: Color = Color::rgb(57, 168, 20); // grass-green
pub const GREEN_DARK: Color = Color::rgb(48, 147, 15);
pub const BLUE: Color = Color::rgb(0, 86, 190); // blue
pub const OFF_WHITE: Color = Color::rgb(222, 222, 222); // very light grey
pub const GREY_LIGHT: Color = Color::rgb(168, 168, 168); // greyish
pub const GREY_MEDIUM: Color = Color::rgb(100, 100, 100);
pub const GREY_DARK: Color = Color::rgb(51, 51, 51); // greyer

// Commonly used corner radius (i.e. for buttons).
pub const RADIUS: u8 = 2;

// Size of icons in the UI (i.e. inside buttons).
pub const ICON_SIZE: i32 = 16;

// UI icons.
pub const ICON_CANCEL: &[u8] = include_res!("model_tt/res/cancel.toif");
pub const ICON_CONFIRM: &[u8] = include_res!("model_tt/res/confirm.toif");
pub const ICON_SPACE: &[u8] = include_res!("model_tt/res/space.toif");
pub const ICON_BACK: &[u8] = include_res!("model_tt/res/back.toif");
pub const ICON_CLICK: &[u8] = include_res!("model_tt/res/click.toif");
pub const ICON_NEXT: &[u8] = include_res!("model_tt/res/next.toif");

// Scrollbar/PIN dots.
pub const DOT_ACTIVE: &[u8] = include_res!("model_tt/res/scroll-active.toif");
pub const DOT_INACTIVE: &[u8] = include_res!("model_tt/res/scroll-inactive.toif");

pub fn label_default() -> LabelStyle {
    LabelStyle {
        font: FONT_NORMAL,
        text_color: FG,
        background_color: BG,
    }
}

pub fn label_keyboard() -> LabelStyle {
    LabelStyle {
        font: FONT_MEDIUM,
        text_color: OFF_WHITE,
        background_color: BG,
    }
}

pub fn label_keyboard_warning() -> LabelStyle {
    LabelStyle {
        font: FONT_MEDIUM,
        text_color: RED,
        background_color: BG,
    }
}

pub fn label_keyboard_minor() -> LabelStyle {
    LabelStyle {
        font: FONT_NORMAL,
        text_color: OFF_WHITE,
        background_color: BG,
    }
}

pub fn button_default() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: FONT_BOLD,
            text_color: FG,
            button_color: GREY_DARK,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: FONT_BOLD,
            text_color: FG,
            button_color: GREY_MEDIUM,
            background_color: BG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: FONT_BOLD,
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
            font: FONT_BOLD,
            text_color: FG,
            button_color: GREEN,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: FONT_BOLD,
            text_color: FG,
            button_color: GREEN_DARK,
            background_color: BG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: FONT_BOLD,
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
            font: FONT_BOLD,
            text_color: FG,
            button_color: RED,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: FONT_BOLD,
            text_color: FG,
            button_color: RED_DARK,
            background_color: BG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: FONT_BOLD,
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
            font: FONT_BOLD,
            text_color: FG,
            button_color: YELLOW,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: FONT_BOLD,
            text_color: FG,
            button_color: YELLOW_DARK,
            background_color: BG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: FONT_BOLD,
            text_color: GREY_LIGHT,
            button_color: YELLOW,
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
            font: FONT_MONO,
            text_color: FG,
            button_color: GREY_DARK,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: FONT_MONO,
            text_color: FG,
            button_color: GREY_MEDIUM,
            background_color: BG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: FONT_MONO,
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

pub struct TTDefaultText;

impl DefaultTextTheme for TTDefaultText {
    const BACKGROUND_COLOR: Color = BG;
    const TEXT_FONT: Font = FONT_NORMAL;
    const TEXT_COLOR: Color = FG;
    const HYPHEN_FONT: Font = FONT_BOLD;
    const HYPHEN_COLOR: Color = GREY_LIGHT;
    const ELLIPSIS_FONT: Font = FONT_BOLD;
    const ELLIPSIS_COLOR: Color = GREY_LIGHT;

    const NORMAL_FONT: Font = FONT_NORMAL;
    const MEDIUM_FONT: Font = FONT_MEDIUM;
    const BOLD_FONT: Font = FONT_BOLD;
    const MONO_FONT: Font = FONT_MONO;
}

pub const CONTENT_BORDER: i32 = 5;
pub const KEYBOARD_SPACING: i32 = 8;

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
