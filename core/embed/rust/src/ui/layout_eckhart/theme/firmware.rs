use crate::{
    time::Duration,
    ui::component::text::{
        layout::{Chunks, LineBreaking, PageBreaking},
        TextStyle,
    },
};

use super::{
    super::{
        component::{ButtonStyle, ButtonStyleSheet},
        fonts,
    },
    *,
};

pub const LOCK_HOLD_DURATION: Duration = Duration::from_millis(1500);
pub const CONFIRM_HOLD_DURATION: Duration = Duration::from_millis(1500);
pub const ERASE_HOLD_DURATION: Duration = Duration::from_millis(1500);

// Text styles
/// Alias for use with copied code, might be deleted later
pub const TEXT_NORMAL: TextStyle = TEXT_MEDIUM;
/// TT Satoshi Extra Light - 72 (PIN keyboard, Wallet backup / word)
pub const TEXT_SUPER_BIG: TextStyle = TextStyle::new(
    fonts::FONT_SATOSHI_EXTRALIGHT_72,
    GREY_EXTRA_LIGHT,
    BG,
    GREY_EXTRA_LIGHT,
    GREY_EXTRA_LIGHT,
);
/// TT Satoshi Extra Light - 46 (Char keyboard, Backup check)
pub const TEXT_BIG: TextStyle = TextStyle::new(
    fonts::FONT_SATOSHI_EXTRALIGHT_46,
    GREY_EXTRA_LIGHT,
    BG,
    GREY_EXTRA_LIGHT,
    GREY_EXTRA_LIGHT,
);
/// TT Satoshi Regular - 38 (Screen text, Menu item label)
pub const TEXT_REGULAR: TextStyle = TextStyle::new(
    fonts::FONT_SATOSHI_REGULAR_38,
    GREY_LIGHT,
    BG,
    GREY_LIGHT,
    GREY_LIGHT,
);
/// TT Satoshi Medium - 26 (Screen text, Button label, Input value)
pub const TEXT_MEDIUM: TextStyle = TextStyle::new(
    fonts::FONT_SATOSHI_MEDIUM_26,
    GREY_LIGHT,
    BG,
    GREY_LIGHT,
    GREY_LIGHT,
);
/// TT Satoshi Regular - 22 (Screen title, Hint, PageCounter, Secondary info)
/// with negative line spacing to make it more compact
pub const TEXT_SMALL: TextStyle =
    TextStyle::new(fonts::FONT_SATOSHI_REGULAR_22, GREY, BG, GREY, GREY).with_line_spacing(-4);
/// Roboto Mono Medium - 38 (Number value)
pub const TEXT_MONO_MEDIUM: TextStyle = TextStyle::new(
    fonts::FONT_MONO_MEDIUM_38,
    GREY_EXTRA_LIGHT,
    BG,
    GREY_EXTRA_LIGHT,
    GREY_EXTRA_LIGHT,
);

pub const TEXT_MONO_MEDIUM_LIGHT: TextStyle = TextStyle::new(
    fonts::FONT_MONO_MEDIUM_38,
    GREY_LIGHT,
    BG,
    GREY_LIGHT,
    GREY_LIGHT,
)
.with_line_breaking(LineBreaking::BreakWordsNoHyphen);

/// Roboto Mono Light - 30 (Address, data)
pub const TEXT_MONO_LIGHT: TextStyle = TextStyle::new(
    fonts::FONT_MONO_LIGHT_30,
    GREY_LIGHT,
    BG,
    GREY_LIGHT,
    GREY_LIGHT,
)
.with_line_breaking(LineBreaking::BreakWordsNoHyphen);

pub const TEXT_REGULAR_WARNING: TextStyle =
    TextStyle::new(fonts::FONT_SATOSHI_REGULAR_38, RED, BG, GREY, GREY);

pub const TEXT_MEDIUM_EXTRA_LIGHT: TextStyle = TextStyle::new(
    fonts::FONT_SATOSHI_MEDIUM_26,
    GREY_EXTRA_LIGHT,
    BG,
    GREY_EXTRA_LIGHT,
    GREY_EXTRA_LIGHT,
);

pub const TEXT_SMALL_LIGHT: TextStyle = TextStyle::new(
    fonts::FONT_SATOSHI_REGULAR_22,
    GREY_LIGHT,
    BG,
    GREY_LIGHT,
    GREY_LIGHT,
)
.with_line_spacing(-4);

/// Makes sure that the displayed text (usually address) will get divided into
/// smaller chunks.
pub const TEXT_MONO_ADDRESS_CHUNKS: TextStyle = TEXT_MONO_LIGHT
    .with_chunks(Chunks::new(4, 8))
    .with_line_spacing(24);

pub const TEXT_MONO_ADDRESS: TextStyle = TEXT_MONO_LIGHT
    .with_line_breaking(LineBreaking::BreakWordsNoHyphen)
    .with_page_breaking(PageBreaking::CutAndInsertEllipsis);

/// Decide the text style of chunkified text according to its length.
pub fn get_chunkified_text_style(_character_length: usize) -> &'static TextStyle {
    &TEXT_MONO_ADDRESS_CHUNKS
}

pub const TEXT_MONO_EXTRA_LIGHT: TextStyle = TextStyle::new(
    fonts::FONT_MONO_LIGHT_30,
    GREY_EXTRA_LIGHT,
    BG,
    GREY_EXTRA_LIGHT,
    GREY_EXTRA_LIGHT,
);

pub const TEXT_CHECKLIST_INACTIVE: TextStyle = TextStyle::new(
    fonts::FONT_SATOSHI_MEDIUM_26,
    GREY_DARK,
    BG,
    GREY_DARK,
    GREY_DARK,
);

// Macro for styles differing only in text color
macro_rules! label_title {
    ($color:expr) => {
        TextStyle::new(fonts::FONT_SATOSHI_REGULAR_22, $color, BG, $color, $color)
            .with_line_spacing(-4)
    };
}

pub const fn label_title_main() -> TextStyle {
    label_title!(GREY)
}

pub const fn label_title_confirm() -> TextStyle {
    label_title!(GREEN_LIGHT)
}

pub const fn label_title_danger() -> TextStyle {
    label_title!(ORANGE)
}

pub const fn label_title_warning() -> TextStyle {
    label_title!(YELLOW)
}

pub const fn label_menu_item_subtitle() -> TextStyle {
    TextStyle::new(fonts::FONT_SATOSHI_REGULAR_22, GREY, BG, GREY, GREY)
}

pub const fn label_menu_item_subtitle_green() -> TextStyle {
    TextStyle::new(fonts::FONT_SATOSHI_REGULAR_22, GREEN, BG, GREEN, GREEN)
}

// Button styles
pub const fn button_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREEN_LIGHT,
            button_color: GREEN_DARK,
            icon_color: GREEN_LIGHT,
            background_color: GREEN_DARK,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREEN,
            button_color: GREEN_EXTRA_DARK,
            icon_color: GREEN,
            background_color: BG,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: GREY_DARK,
            icon_color: GREY_LIGHT,
            background_color: GREY_DARK,
        },
    }
}

pub const fn button_cancel() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_22, // unused
            text_color: ORANGE,                   // unused
            button_color: BG,
            icon_color: ORANGE,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_22, // unused
            text_color: ORANGE_DIMMED,            //unused
            button_color: ORANGE_EXTRA_DARK,
            icon_color: ORANGE_DIMMED,
            background_color: ORANGE_EXTRA_DARK,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_22, // unused
            text_color: GREY_EXTRA_DARK,          // unused
            button_color: BG,
            icon_color: GREY_EXTRA_DARK,
            background_color: BG,
        },
    }
}

pub const fn button_default_actionbar_right() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: GREY_EXTRA_DARK,
            icon_color: GREY_LIGHT,
            background_color: GREY_EXTRA_DARK,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_DARK,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_DARK,
            background_color: BG,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_EXTRA_DARK,
            button_color: BG,
            icon_color: GREY_EXTRA_DARK,
            background_color: BG,
        },
    }
}

pub const fn button_warning_high() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: ORANGE,
            button_color: BG,
            icon_color: ORANGE,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: ORANGE,
            button_color: GREY_SUPER_DARK,
            icon_color: GREEN,
            background_color: BG,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: ORANGE,
            button_color: GREY_DARK,
            icon_color: GREY_LIGHT,
            background_color: GREY_DARK,
        },
    }
}

pub const fn button_header() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: BG,
            icon_color: GREY_LIGHT,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_LIGHT,
            background_color: BG,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: BG,
            icon_color: GREY_LIGHT,
            background_color: BG,
        },
    }
}

// Macro for styles differing only in text color
macro_rules! menu_item_title {
    ($color:expr) => {
        ButtonStyleSheet {
            normal: &ButtonStyle {
                font: fonts::FONT_SATOSHI_REGULAR_38,
                text_color: $color,
                button_color: BG,
                icon_color: $color,
                background_color: BG,
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
                button_color: BG,
                icon_color: GREY_DARK,
                background_color: BG,
            },
        }
    };
}

pub const fn menu_item_title() -> ButtonStyleSheet {
    menu_item_title!(GREY_LIGHT)
}

pub const fn menu_item_title_yellow() -> ButtonStyleSheet {
    menu_item_title!(YELLOW)
}

pub const fn menu_item_title_orange() -> ButtonStyleSheet {
    menu_item_title!(ORANGE)
}

pub const fn menu_item_title_red() -> ButtonStyleSheet {
    menu_item_title!(RED)
}

macro_rules! button_homebar_style {
    ($text_color:expr, $icon_color:expr) => {
        ButtonStyleSheet {
            normal: &ButtonStyle {
                font: fonts::FONT_SATOSHI_MEDIUM_26,
                text_color: $text_color,
                button_color: BG,
                icon_color: $icon_color,
                background_color: BG,
            },
            active: &ButtonStyle {
                font: fonts::FONT_SATOSHI_MEDIUM_26,
                text_color: GREY_LIGHT,
                button_color: GREY_SUPER_DARK,
                icon_color: GREY_LIGHT,
                background_color: GREY_SUPER_DARK,
            },
            disabled: &ButtonStyle {
                font: fonts::FONT_SATOSHI_MEDIUM_26,
                text_color: GREY_LIGHT,
                button_color: GREY_SUPER_DARK,
                icon_color: GREY_LIGHT,
                background_color: GREY_SUPER_DARK,
            },
        }
    };
}
pub const fn button_homebar_style(level: u8) -> ButtonStyleSheet {
    // NOTE: 0 is the highest severity.
    match level {
        4 => button_homebar_style!(GREY_LIGHT, GREY_LIGHT),
        3 => button_homebar_style!(GREY_LIGHT, GREEN_LIME),
        2 => button_homebar_style!(GREY_LIGHT, YELLOW),
        1 => button_homebar_style!(GREY_LIGHT, YELLOW),
        _ => button_homebar_style!(RED, RED),
    }
}

pub const fn button_select_word() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_EXTRALIGHT_46,
            text_color: GREY_EXTRA_LIGHT,
            button_color: BG,
            icon_color: GREY_EXTRA_LIGHT,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_EXTRALIGHT_46,
            text_color: GREY_DARK,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_DARK,
            background_color: GREY_SUPER_DARK,
        },
        // unused
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_EXTRALIGHT_46,
            text_color: BG,
            button_color: BG,
            icon_color: BG,
            background_color: BG,
        },
    }
}

pub const fn button_keyboard() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_EXTRALIGHT_46,
            text_color: GREY_EXTRA_LIGHT,
            button_color: BG,
            icon_color: GREY_LIGHT,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_EXTRALIGHT_46,
            text_color: GREY_DARK,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_DARK,
            background_color: GREY_SUPER_DARK,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_EXTRALIGHT_46,
            text_color: GREY_EXTRA_DARK,
            button_color: BG,
            icon_color: GREY_EXTRA_DARK,
            background_color: BG,
        },
    }
}

pub const fn button_keyboard_numeric() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_EXTRALIGHT_72,
            text_color: GREY_EXTRA_LIGHT,
            button_color: BG,
            icon_color: GREY_LIGHT,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_EXTRALIGHT_72,
            text_color: GREY_DARK,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_DARK,
            background_color: GREY_SUPER_DARK,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_EXTRALIGHT_72,
            text_color: GREY_EXTRA_DARK,
            button_color: BG,
            icon_color: GREY_EXTRA_DARK,
            background_color: BG,
        },
    }
}

pub const fn button_keyboard_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_22, // unused
            text_color: GREEN_LIGHT,              // unused
            button_color: BG,
            icon_color: GREEN_LIGHT,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_22, // unused
            text_color: GREEN,                    // unused
            button_color: GREEN_EXTRA_DARK,
            icon_color: GREEN,
            background_color: GREEN_EXTRA_DARK,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_22, // unused
            text_color: GREY_EXTRA_DARK,          // unused
            button_color: BG,
            icon_color: GREY_EXTRA_DARK,
            background_color: BG,
        },
    }
}

pub const fn button_keyboard_next() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_EXTRA_LIGHT,
            button_color: BG,
            icon_color: GREY_EXTRA_LIGHT,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_DARK,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_DARK,
            background_color: GREY_SUPER_DARK,
        },
        // not used
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: BG,
            button_color: BG,
            icon_color: BG,
            background_color: BG,
        },
    }
}

pub const fn input_mnemonic() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: BG,
            icon_color: GREY_LIGHT,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_LIGHT,
            background_color: GREY_SUPER_DARK,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: BG,
            icon_color: GREY_LIGHT,
            background_color: BG,
        },
    }
}

pub const fn input_mnemonic_suggestion() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_DARK,
            button_color: BG,
            icon_color: GREY_DARK,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: BG,
            icon_color: GREY_LIGHT,
            background_color: BG,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: BG,
            button_color: BG,
            icon_color: BG,
            background_color: BG,
        },
    }
}

pub const fn input_mnemonic_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREEN_LIGHT,
            button_color: BG,
            icon_color: GREEN_LIGHT,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREEN_LIGHT,
            button_color: GREEN_EXTRA_DARK,
            icon_color: GREEN_LIGHT,
            background_color: GREEN_EXTRA_DARK,
        },
        disabled: &ButtonStyle {
            // unused
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: BG,
            button_color: BG,
            icon_color: BG,
            background_color: BG,
        },
    }
}
