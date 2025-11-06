use crate::{
    time::ShortDuration,
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

// props settings
pub const PROP_INNER_SPACING: i16 = 12; // [px]
pub const PROPS_SPACING: i16 = 16; // [px]
pub const PROPS_KEY_FONT: TextStyle = TEXT_SMALL_LIGHT;
pub const PROPS_VALUE_FONT: TextStyle = TEXT_MONO_LIGHT;
pub const PROPS_VALUE_MONO_FONT: TextStyle = TEXT_MONO_LIGHT;

pub const CONFIRM_HOLD_DURATION: ShortDuration = ShortDuration::from_millis(1500);
pub const ERASE_HOLD_DURATION: ShortDuration = ShortDuration::from_millis(1500);
/// Duration for the battery status showcase on the ActionBar or Header
pub const FUEL_GAUGE_DURATION: ShortDuration = ShortDuration::from_millis(2000);

// Text styles
/// TT Satoshi Extra Light - 72 (PIN keyboard, Wallet backup / word)
pub const TEXT_SUPER_BIG: TextStyle = TextStyle::new(
    fonts::FONT_SATOSHI_EXTRALIGHT_72,
    GREY_EXTRA_LIGHT,
    BG,
    GREY_LIGHT,
    GREY_LIGHT,
);
/// TT Satoshi Extra Light - 46 (Char keyboard, Backup check)
pub const TEXT_BIG: TextStyle = TextStyle::new(
    fonts::FONT_SATOSHI_EXTRALIGHT_46,
    GREY_EXTRA_LIGHT,
    BG,
    GREY,
    GREY,
)
.with_line_breaking(LineBreaking::BreakWordsNoHyphen);
/// TT Satoshi Regular - 38 (Screen text, Menu item label)
pub const TEXT_REGULAR: TextStyle =
    TextStyle::new(fonts::FONT_SATOSHI_REGULAR_38, GREY_LIGHT, BG, GREY, GREY);
pub const TEXT_REGULAR_ELLIPSIS: TextStyle = TEXT_REGULAR
    .with_line_breaking(LineBreaking::BreakWordsNoHyphen)
    .with_page_breaking(PageBreaking::CutAndInsertEllipsisBoth);
/// TT Satoshi Medium - 26 (Screen text, Button label, Input value)
pub const TEXT_MEDIUM: TextStyle =
    TextStyle::new(fonts::FONT_SATOSHI_MEDIUM_26, GREY_LIGHT, BG, GREY, GREY);

pub const TEXT_MEDIUM_GREY: TextStyle = TextStyle::new(
    fonts::FONT_SATOSHI_MEDIUM_26,
    GREY,
    BG,
    GREY_DARK,
    GREY_DARK,
);

/// TT Satoshi Regular - 22 (Screen title, Hint, PageCounter, Secondary info)
/// with negative line spacing to make it more compact
pub const TEXT_SMALL: TextStyle = TextStyle::new(
    fonts::FONT_SATOSHI_REGULAR_22,
    GREY,
    BG,
    GREY_DARK,
    GREY_DARK,
)
.with_line_spacing(-4);
pub const TEXT_SMALL_BLACK: TextStyle = TextStyle {
    text_color: BG,
    ..TEXT_SMALL
};
/// Roboto Mono Medium - 38 (Number value)
pub const TEXT_MONO_MEDIUM: TextStyle = TextStyle::new(
    fonts::FONT_MONO_MEDIUM_38,
    GREY_EXTRA_LIGHT,
    BG,
    GREY_LIGHT,
    GREY_LIGHT,
)
.with_line_breaking(LineBreaking::BreakAtWhitespace);

pub const TEXT_MONO_MEDIUM_LIGHT: TextStyle =
    TextStyle::new(fonts::FONT_MONO_MEDIUM_38, GREY_LIGHT, BG, GREY, GREY)
        .with_line_breaking(LineBreaking::BreakAtWhitespace)
        .with_page_breaking(PageBreaking::CutAndInsertEllipsisBoth);

pub const TEXT_MONO_MEDIUM_LIGHT_DATA: TextStyle = TEXT_MONO_MEDIUM_LIGHT
    .with_line_breaking(LineBreaking::BreakWordsNoHyphen)
    .with_page_breaking(PageBreaking::CutAndInsertEllipsisBoth);

/// Roboto Mono Light - 30 (Address, data)
pub const TEXT_MONO_LIGHT: TextStyle =
    TextStyle::new(fonts::FONT_MONO_LIGHT_30, GREY_LIGHT, BG, GREY, GREY)
        .with_line_breaking(LineBreaking::BreakWordsNoHyphen);

pub const TEXT_MONO_LIGHT_ELLIPSIS: TextStyle =
    TextStyle::new(fonts::FONT_MONO_LIGHT_30, GREY_LIGHT, BG, GREY, GREY)
        .with_line_breaking(LineBreaking::BreakWordsNoHyphen)
        .with_page_breaking(PageBreaking::CutAndInsertEllipsisBoth);

pub const TEXT_REGULAR_WARNING: TextStyle =
    TextStyle::new(fonts::FONT_SATOSHI_REGULAR_38, RED, BG, FG, FG);

pub const TEXT_MEDIUM_EXTRA_LIGHT: TextStyle = TextStyle::new(
    fonts::FONT_SATOSHI_MEDIUM_26,
    GREY_EXTRA_LIGHT,
    BG,
    GREY_LIGHT,
    GREY_LIGHT,
);

pub const TEXT_SMALL_LIGHT: TextStyle =
    TextStyle::new(fonts::FONT_SATOSHI_REGULAR_22, GREY_LIGHT, BG, GREY, GREY)
        .with_line_spacing(-4);

/// Makes sure that the displayed text (usually address) will get divided into
/// smaller chunks.
pub const TEXT_MONO_ADDRESS_CHUNKS: TextStyle = TEXT_MONO_MEDIUM_LIGHT
    .with_chunks(Chunks::new(4, 13).with_max_rows(5))
    .with_line_spacing(22)
    .with_page_breaking(PageBreaking::CutAndInsertEllipsisBoth);

pub const TEXT_MONO_ADDRESS: TextStyle = TEXT_MONO_MEDIUM_LIGHT
    .with_line_breaking(LineBreaking::BreakWordsNoHyphen)
    .with_page_breaking(PageBreaking::CutAndInsertEllipsisBoth);

pub const TEXT_MONO_EXTRA_LIGHT: TextStyle = TextStyle::new(
    fonts::FONT_MONO_LIGHT_30,
    GREY_EXTRA_LIGHT,
    BG,
    GREY_LIGHT,
    GREY_LIGHT,
);

pub const TEXT_CHECKLIST_INACTIVE: TextStyle = TextStyle::new(
    fonts::FONT_SATOSHI_MEDIUM_26,
    GREY_DARK,
    BG,
    GREY_EXTRA_DARK,
    GREY_EXTRA_DARK,
);

pub const TEXT_MENU_ITEM_SUBTITLE: TextStyle = TextStyle::new(
    fonts::FONT_SATOSHI_REGULAR_22,
    GREY,
    BG,
    GREY_DARK,
    GREY_DARK,
);

pub const TEXT_MENU_ITEM_SUBTITLE_GREEN: TextStyle = TextStyle::new(
    fonts::FONT_SATOSHI_REGULAR_22,
    GREEN,
    BG,
    GREEN_DARK,
    GREEN_DARK,
);

const fn label_title(color: Color) -> TextStyle {
    TextStyle::new(fonts::FONT_SATOSHI_REGULAR_22, color, BG, color, color).with_line_spacing(-4)
}

pub const fn label_title_main() -> TextStyle {
    label_title(GREY)
}

pub const fn label_title_confirm() -> TextStyle {
    label_title(GREEN_LIGHT)
}

pub const fn label_title_danger() -> TextStyle {
    label_title(ORANGE)
}

pub const fn label_title_warning() -> TextStyle {
    label_title(YELLOW)
}

// Button styles
pub const fn button_default() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: BG,
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
            text_color: GREY,
            button_color: BG,
            icon_color: GREY_EXTRA_DARK,
        },
    }
}

pub const fn button_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREEN_LIGHT,
            button_color: GREEN_DARK,
            icon_color: GREEN_LIGHT,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREEN,
            button_color: GREEN_EXTRA_DARK,
            icon_color: GREEN,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: GREY_DARK,
            icon_color: GREY_LIGHT,
        },
    }
}

pub const fn button_cancel() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: ORANGE,
            button_color: BG,
            icon_color: ORANGE,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: ORANGE_DIMMED,
            button_color: ORANGE_EXTRA_DARK,
            icon_color: ORANGE_DIMMED,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_EXTRA_DARK,
            button_color: BG,
            icon_color: GREY_EXTRA_DARK,
        },
    }
}

pub const fn button_actionbar_right_default() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: GREY_EXTRA_DARK,
            icon_color: GREY_LIGHT,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_DARK,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_DARK,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_EXTRA_DARK,
            button_color: BG,
            icon_color: GREY_EXTRA_DARK,
        },
    }
}

pub const fn button_actionbar_danger() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: ORANGE,
            button_color: ORANGE_SUPER_DARK,
            icon_color: ORANGE,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: ORANGE_DIMMED,
            button_color: ORANGE_DARK,
            icon_color: ORANGE_DIMMED,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: ORANGE,
            button_color: GREY_DARK,
            icon_color: GREY_LIGHT,
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
            button_color: BG,
            icon_color: GREY_LIGHT,
        },
    }
}

pub const fn button_header_inverted() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: BG,
            button_color: FG,
            icon_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_DARK,
            button_color: GREY_LIGHT,
            icon_color: GREY_DARK,
        },
        // unused
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_LIGHT,
            button_color: GREY_EXTRA_LIGHT,
            icon_color: GREY_LIGHT,
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
                button_color: BG,
                icon_color: GREY_DARK,
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
    ($icon_color:expr) => {
        ButtonStyleSheet {
            normal: &ButtonStyle {
                font: fonts::FONT_SATOSHI_MEDIUM_26,
                text_color: GREY_LIGHT,
                button_color: GREY_SUPER_DARK,
                icon_color: $icon_color,
            },
            active: &ButtonStyle {
                font: fonts::FONT_SATOSHI_MEDIUM_26,
                text_color: GREY_LIGHT,
                button_color: GREY_SUPER_DARK,
                icon_color: GREY_LIGHT,
            },
            // unused
            disabled: &ButtonStyle {
                font: fonts::FONT_SATOSHI_MEDIUM_26,
                text_color: GREY_LIGHT,
                button_color: GREY_SUPER_DARK,
                icon_color: GREY_LIGHT,
            },
        }
    };
}
pub const fn button_homebar_style(notification_level: u8) -> (ButtonStyleSheet, Gradient) {
    // NOTE: 0 is the highest severity.
    match notification_level {
        0 => (button_homebar_style!(RED), Gradient::Alert),
        1 => (button_homebar_style!(GREY_LIGHT), Gradient::Warning),
        2 => (button_homebar_style!(GREY_LIGHT), Gradient::DefaultGrey),
        3 => (button_homebar_style!(GREY_LIGHT), Gradient::SignGreen),
        _ => (button_homebar_style!(GREY_LIGHT), Gradient::DefaultGrey),
    }
}

pub const fn button_select_word() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_EXTRALIGHT_46,
            text_color: GREY_EXTRA_LIGHT,
            button_color: BG,
            icon_color: GREY_EXTRA_LIGHT,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_EXTRALIGHT_46,
            text_color: GREY_DARK,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_DARK,
        },
        // unused
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_EXTRALIGHT_46,
            text_color: BG,
            button_color: BG,
            icon_color: BG,
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
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_EXTRALIGHT_46,
            text_color: GREY_DARK,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_DARK,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_EXTRALIGHT_46,
            text_color: GREY_EXTRA_DARK,
            button_color: BG,
            icon_color: GREY_EXTRA_DARK,
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
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_EXTRALIGHT_72,
            text_color: GREY_DARK,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_DARK,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_EXTRALIGHT_72,
            text_color: GREY_EXTRA_DARK,
            button_color: BG,
            icon_color: GREY_EXTRA_DARK,
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
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_22, // unused
            text_color: GREEN,                    // unused
            button_color: GREEN_EXTRA_DARK,
            icon_color: GREEN,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_22, // unused
            text_color: GREY_EXTRA_DARK,          // unused
            button_color: BG,
            icon_color: GREY_EXTRA_DARK,
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
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREY_DARK,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_DARK,
        },
        // not used
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: BG,
            button_color: BG,
            icon_color: BG,
        },
    }
}

// Things that look like button but don't do anything.
pub const fn button_always_disabled() -> ButtonStyleSheet {
    let style = &ButtonStyle {
        font: fonts::FONT_SATOSHI_MEDIUM_26,
        text_color: GREY,
        button_color: BG,
        icon_color: GREY,
    };
    ButtonStyleSheet {
        normal: style,
        active: style,
        disabled: style,
    }
}

pub const fn button_menu_tutorial() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREEN_LIME,
            button_color: BG,
            icon_color: GREEN_LIME,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: GREEN_LIME,
            button_color: GREEN_EXTRA_DARK,
            icon_color: GREEN_LIME,
        },
        // not used
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_MEDIUM_26,
            text_color: BG,
            button_color: BG,
            icon_color: BG,
        },
    }
}

pub const fn input_mnemonic() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_38,
            text_color: GREY_LIGHT,
            button_color: BG,
            icon_color: GREY_LIGHT,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_38,
            text_color: GREY_LIGHT,
            button_color: GREY_SUPER_DARK,
            icon_color: GREY_LIGHT,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_38,
            text_color: GREY_LIGHT,
            button_color: BG,
            icon_color: GREY_LIGHT,
        },
    }
}

pub const fn input_mnemonic_suggestion() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_38,
            text_color: GREY_DARK,
            button_color: BG,
            icon_color: GREY_DARK,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_38,
            text_color: GREY_LIGHT,
            button_color: BG,
            icon_color: GREY_LIGHT,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_38,
            text_color: BG,
            button_color: BG,
            icon_color: BG,
        },
    }
}

pub const fn input_mnemonic_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_38,
            text_color: GREEN_LIGHT,
            button_color: BG,
            icon_color: GREEN_LIGHT,
        },
        active: &ButtonStyle {
            font: fonts::FONT_SATOSHI_REGULAR_38,
            text_color: GREEN_LIGHT,
            button_color: GREEN_EXTRA_DARK,
            icon_color: GREEN_LIGHT,
        },
        disabled: &ButtonStyle {
            // unused
            font: fonts::FONT_SATOSHI_REGULAR_38,
            text_color: BG,
            button_color: BG,
            icon_color: BG,
        },
    }
}
