use crate::ui::{
    component::{text::TextStyle, LineBreaking::BreakWordsNoHyphen},
    display::Color,
};

use super::{
    super::{
        component::{ButtonStyle, ButtonStyleSheet},
        fonts,
    },
    BLACK, BLUE, GREY, GREY_DARK, GREY_EXTRA_LIGHT, GREY_LIGHT, GREY_SUPER_DARK, RED, WHITE,
};

pub const BLD_BG: Color = BLACK;
pub const BLD_FG: Color = WHITE;

pub const WELCOME_COLOR: Color = BLACK;

pub fn button_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_EXTRA_LIGHT,
            button_color: BLUE,
            icon_color: GREY_EXTRA_LIGHT,
            background_color: BLD_BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_EXTRA_LIGHT,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_EXTRA_LIGHT,
            background_color: BLD_BG,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: BLD_FG,
            button_color: GREY_DARK,
            icon_color: BLD_BG,
            background_color: BLD_FG,
        },
    }
}

pub fn button_cancel() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_EXTRA_LIGHT,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_EXTRA_LIGHT,
            background_color: BLD_BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: GREY_DARK,
            icon_color: GREY_LIGHT,
            background_color: BLD_BG,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: BLD_FG,
            button_color: GREY_DARK,
            icon_color: BLD_BG,
            background_color: BLD_FG,
        },
    }
}

pub const fn button_header() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: BLD_BG,
            icon_color: GREY_LIGHT,
            background_color: BLD_BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_LIGHT,
            background_color: BLD_BG,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: BLD_BG,
            icon_color: GREY_LIGHT,
            background_color: BLD_BG,
        },
    }
}

pub fn button_wipe_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_EXTRA_LIGHT,
            button_color: RED,
            icon_color: GREY_EXTRA_LIGHT,
            background_color: RED,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: RED,
            button_color: GREY_EXTRA_LIGHT,
            icon_color: RED,
            background_color: GREY_EXTRA_LIGHT,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: BLD_FG,
            button_color: GREY_DARK,
            icon_color: BLD_FG,
            background_color: BLD_FG,
        },
    }
}

pub fn button_bld_menu() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_38,
            text_color: GREY_EXTRA_LIGHT,
            button_color: BLD_BG,
            icon_color: GREY_EXTRA_LIGHT,
            background_color: BLD_BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_38,
            text_color: GREY_DARK,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_DARK,
            background_color: GREY_SUPER_DARK,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_38,
            text_color: GREY_DARK,
            button_color: BLD_BG,
            icon_color: GREY_DARK,
            background_color: BLD_BG,
        },
    }
}

pub const fn text_title(bg: Color) -> TextStyle {
    TextStyle::new(fonts::FONT_SATOSHI_MEDIUM_26, GREY, bg, GREY, GREY)
}

pub const TEXT_FW_FINGERPRINT: TextStyle = TextStyle::new(
    fonts::FONT_SATOSHI_REGULAR_38,
    GREY_EXTRA_LIGHT,
    BLD_BG,
    BLD_FG,
    BLD_FG,
)
.with_line_breaking(BreakWordsNoHyphen);

pub const TEXT_WARNING: TextStyle =
    TextStyle::new(fonts::FONT_SATOSHI_REGULAR_38, RED, BLD_BG, RED, RED);
