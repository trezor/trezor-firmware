use crate::ui::{
    component::text::{formatted::FormattedFonts, TextStyle},
    display::{Color, Font},
};

use super::component::{ButtonStyle, ButtonStyleSheet};

// Color palette.
pub const WHITE: Color = Color::rgb(255, 255, 255);
pub const BLACK: Color = Color::rgb(0, 0, 0);
pub const GREY_LIGHT: Color = WHITE; // Word/page break characters.
pub const FG: Color = WHITE; // Default foreground (text & icon) color.
pub const BG: Color = BLACK; // Default background color.

pub fn button_default() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::BOLD,
            text_color: BG,
            border_horiz: true,
        },
        active: &ButtonStyle {
            font: Font::BOLD,
            text_color: FG,
            border_horiz: true,
        },
    }
}

pub fn button_cancel() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::BOLD,
            text_color: FG,
            border_horiz: false,
        },
        active: &ButtonStyle {
            font: Font::BOLD,
            text_color: BG,
            border_horiz: false,
        },
    }
}

pub const TEXT_NORMAL: TextStyle = TextStyle::new(Font::NORMAL, FG, BG, FG, FG);
pub const TEXT_DEMIBOLD: TextStyle = TextStyle::new(Font::DEMIBOLD, FG, BG, FG, FG);
pub const TEXT_BOLD: TextStyle = TextStyle::new(Font::BOLD, FG, BG, FG, FG);
pub const TEXT_MONO: TextStyle = TextStyle::new(Font::MONO, FG, BG, FG, FG);

pub const FORMATTED: FormattedFonts = FormattedFonts {
    normal: Font::NORMAL,
    demibold: Font::DEMIBOLD,
    bold: Font::BOLD,
    mono: Font::MONO,
};
