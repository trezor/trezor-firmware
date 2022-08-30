use crate::ui::{
    component::text::TextStyle,
    display::{Color, Font},
    model_tr::component::{LoaderStyle, LoaderStyleSheet},
};

use super::component::{ButtonStyle, ButtonStyleSheet};

// Font constants.
pub const FONT_NORMAL: Font = Font::new(-1);
pub const FONT_MEDIUM: Font = Font::new(-5);
pub const FONT_BOLD: Font = Font::new(-2);
pub const FONT_MONO: Font = Font::new(-3);

// Color palette.
pub const WHITE: Color = Color::rgb(255, 255, 255);
pub const BLACK: Color = Color::rgb(0, 0, 0);
pub const GREY_LIGHT: Color = WHITE; // Word/page break characters.
pub const FG: Color = WHITE; // Default foreground (text & icon) color.
pub const BG: Color = BLACK; // Default background color.

pub const ICON_SUCCESS: &[u8] = include_res!("model_tr/res/success.toif");
pub const ICON_FAIL: &[u8] = include_res!("model_tr/res/fail.toif");

pub fn button_default() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: FONT_BOLD,
            text_color: BG,
            border_horiz: true,
        },
        active: &ButtonStyle {
            font: FONT_BOLD,
            text_color: FG,
            border_horiz: true,
        },
    }
}

pub fn button_cancel() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: FONT_BOLD,
            text_color: FG,
            border_horiz: false,
        },
        active: &ButtonStyle {
            font: FONT_BOLD,
            text_color: BG,
            border_horiz: false,
        },
    }
}

pub fn loader_default() -> LoaderStyleSheet {
    LoaderStyleSheet {
        normal: &LoaderStyle {
            font: FONT_NORMAL,
            fg_color: FG,
            bg_color: BG,
        },
    }
}

pub const TEXT_NORMAL: TextStyle = TextStyle::new(FONT_NORMAL, FG, BG, FG, FG);
pub const TEXT_MEDIUM: TextStyle = TextStyle::new(FONT_MEDIUM, FG, BG, FG, FG);
pub const TEXT_BOLD: TextStyle = TextStyle::new(FONT_BOLD, FG, BG, FG, FG);
pub const TEXT_MONO: TextStyle = TextStyle::new(FONT_MONO, FG, BG, FG, FG);
