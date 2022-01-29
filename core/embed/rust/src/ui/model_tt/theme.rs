use crate::ui::{
    component::{label::LabelStyle, text::DefaultTextTheme},
    display::{Color, Font},
};

use super::component::{ButtonStyle, ButtonStyleSheet};

// Font constants.
pub const FONT_NORMAL: Font = Font::new(-1);
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
pub const YELLOW: Color = Color::rgb(193, 144, 9); // ochre
pub const GREEN: Color = Color::rgb(57, 168, 20); // grass-green
pub const BLUE: Color = Color::rgb(0, 86, 190); // blue
pub const GREY_LIGHT: Color = Color::rgb(168, 168, 168); // greyish
pub const GREY_DARK: Color = Color::rgb(51, 51, 51); // black

// Commonly used corner radius (i.e. for buttons).
pub const RADIUS: u8 = 4;

// Size of icons in the UI (i.e. inside buttons).
pub const ICON_SIZE: i32 = 16;

// UI icons.
pub const ICON_CANCEL: &[u8] = include_res!("cancel.toif");
pub const ICON_CONFIRM: &[u8] = include_res!("confirm.toif");
pub const ICON_SPACE: &[u8] = include_res!("space.toif");

pub fn label_default() -> LabelStyle {
    LabelStyle {
        font: FONT_NORMAL,
        text_color: FG,
        background_color: BG,
    }
}

pub fn button_default() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: FONT_NORMAL,
            text_color: FG,
            button_color: GREY_DARK,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 2,
        },
        active: &ButtonStyle {
            font: FONT_NORMAL,
            text_color: BG,
            button_color: FG,
            background_color: BG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 2,
        },
        disabled: &ButtonStyle {
            font: FONT_NORMAL,
            text_color: GREY_LIGHT,
            button_color: GREY_DARK,
            background_color: BG,
            border_color: BG,
            border_radius: RADIUS,
            border_width: 2,
        },
    }
}

pub fn button_confirm() -> ButtonStyleSheet {
    button_default()
}

pub fn button_cancel() -> ButtonStyleSheet {
    button_default()
}

pub fn button_clear() -> ButtonStyleSheet {
    button_default()
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
    const BOLD_FONT: Font = FONT_BOLD;
    const MONO_FONT: Font = FONT_MONO;
}
