use crate::ui::{
    component::{text::TextStyle, LineBreaking::BreakWordsNoHyphen},
    display::Color,
    util::include_icon,
};

use super::{
    super::{
        component::{ButtonStyle, ButtonStyleSheet},
        fonts,
    },
    BLACK, BLUE, GREY, GREY_DARK, GREY_EXTRA_DARK, GREY_EXTRA_LIGHT, GREY_LIGHT, GREY_SUPER_DARK,
    ORANGE, RED, WHITE,
};

pub const BLD_BG: Color = BLACK;
pub const BLD_FG: Color = WHITE;

pub const WELCOME_COLOR: Color = BLACK;

// UI icons specific to bootloader (white color)
include_icon!(ICON_SEVEN, "layout_eckhart/res/bootloader/7.toif");
include_icon!(
    ICON_QR_TREZOR_IO_SETUP,
    "layout_eckhart/res/bootloader/QRCode_170.toif"
);

pub const fn button_default() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_EXTRA_LIGHT,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_EXTRA_LIGHT,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: GREY_EXTRA_DARK,
            icon_color: GREY_LIGHT,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY,
            button_color: BLD_BG,
            icon_color: GREY,
        },
    }
}

pub fn button_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_EXTRA_LIGHT,
            button_color: BLUE,
            icon_color: GREY_EXTRA_LIGHT,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_EXTRA_LIGHT,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_EXTRA_LIGHT,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: BLD_FG,
            button_color: GREY_DARK,
            icon_color: BLD_BG,
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
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: GREY_DARK,
            icon_color: GREY_LIGHT,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: BLD_FG,
            button_color: GREY_DARK,
            icon_color: BLD_BG,
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
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_LIGHT,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: BLD_BG,
            icon_color: GREY_LIGHT,
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
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: RED,
            button_color: GREY_EXTRA_LIGHT,
            icon_color: RED,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: BLD_FG,
            button_color: GREY_DARK,
            icon_color: BLD_FG,
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
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_38,
            text_color: GREY_DARK,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_DARK,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_38,
            text_color: GREY_DARK,
            button_color: BLD_BG,
            icon_color: GREY_DARK,
        },
    }
}

pub fn button_bld_menu_danger() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_38,
            text_color: ORANGE,
            button_color: BLD_BG,
            icon_color: ORANGE,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_38,
            text_color: GREY_DARK,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_DARK,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_38,
            text_color: GREY_DARK,
            button_color: BLD_BG,
            icon_color: GREY_DARK,
        },
    }
}

/// Button style for the welcome screen
pub fn button_bld_initial_setup() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: BLD_BG,
            icon_color: GREY_LIGHT,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_EXTRA_LIGHT,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_EXTRA_LIGHT,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY,
            button_color: BLD_BG,
            icon_color: GREY,
        },
    }
}

pub const fn text_title(text_color: Color) -> TextStyle {
    TextStyle::new(
        fonts::FONT_SATOSHI_MEDIUM_26,
        text_color,
        BLD_BG,
        text_color,
        text_color,
    )
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
