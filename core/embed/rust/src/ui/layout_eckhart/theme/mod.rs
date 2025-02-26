pub mod bootloader;

pub mod backlight;

use crate::{
    time::Duration,
    ui::{component::text::TextStyle, display::Color, util::include_icon},
};

use super::{
    component::{ButtonStyle, ButtonStyleSheet, ResultStyle},
    fonts,
};

pub const CONFIRM_HOLD_DURATION: Duration = Duration::from_millis(2000);
pub const ERASE_HOLD_DURATION: Duration = Duration::from_millis(1500);

// Color palette.
pub const WHITE: Color = Color::rgb(0xFF, 0xFF, 0xFF);
pub const BLACK: Color = Color::rgb(0, 0, 0);
pub const FG: Color = WHITE; // Default foreground (text & icon) color.
pub const BG: Color = BLACK; // Default background color.
pub const GREY_EXTRA_LIGHT: Color = Color::rgb(0xF0, 0xF0, 0xF0);
pub const GREY_LIGHT: Color = Color::rgb(0xC7, 0xCD, 0xD3);
pub const GREY: Color = Color::rgb(0x8B, 0x8F, 0x93);
pub const GREY_DARK: Color = Color::rgb(0x46, 0x48, 0x4A);
pub const GREY_EXTRA_DARK: Color = Color::rgb(0x16, 0x1F, 0x24);
pub const GREY_SUPER_DARK: Color = Color::rgb(0x0B, 0x10, 0x12);

pub const GREEN_LIME: Color = Color::rgb(0x9B, 0xE8, 0x87);
pub const GREEN_LIGHT: Color = Color::rgb(0x0B, 0xA5, 0x67);
pub const GREEN: Color = Color::rgb(0x08, 0x74, 0x48);
pub const GREEN_DARK: Color = Color::rgb(0x06, 0x1E, 0x19);
pub const GREEN_EXTRA_DARK: Color = Color::rgb(0x03, 0x10, 0x0C);

pub const ORANGE: Color = Color::rgb(0xFF, 0x63, 0x30);
pub const ORANGE_DIMMED: Color = Color::rgb(0x9E, 0x57, 0x42);
pub const ORANGE_DARK: Color = Color::rgb(0x18, 0x0C, 0x0A);
pub const ORANGE_EXTRA_DARK: Color = Color::rgb(0x12, 0x07, 0x04);

pub const YELLOW: Color = Color::rgb(0xFF, 0xE4, 0x58);

pub const RED: Color = Color::rgb(0xFF, 0x30, 0x30);
pub const FATAL_ERROR_COLOR: Color = Color::rgb(0xE7, 0x0E, 0x0E);
pub const FATAL_ERROR_HIGHLIGHT_COLOR: Color = Color::rgb(0xFF, 0x41, 0x41);

// UI icons (white color).
include_icon!(ICON_CHEVRON_DOWN, "layout_eckhart/res/chevron_down.toif");
include_icon!(
    ICON_CHEVRON_DOWN_MINI,
    "layout_eckhart/res/chevron_down_mini.toif"
);
include_icon!(ICON_CHEVRON_LEFT, "layout_eckhart/res/chevron_left.toif");
include_icon!(ICON_CHEVRON_RIGHT, "layout_eckhart/res/chevron_right.toif");
include_icon!(ICON_CHEVRON_UP, "layout_eckhart/res/chevron_up.toif");
include_icon!(ICON_CLOSE, "layout_eckhart/res/close.toif");
include_icon!(ICON_DONE, "layout_eckhart/res/done.toif");
include_icon!(ICON_FORESLASH, "layout_eckhart/res/foreslash.toif");
include_icon!(ICON_INFO, "layout_eckhart/res/info.toif");
include_icon!(ICON_MENU, "layout_eckhart/res/menu.toif");
include_icon!(ICON_WARNING, "layout_eckhart/res/warning.toif");
// Keyboard icons
include_icon!(ICON_ASTERISK, "layout_eckhart/res/keyboard/asterisk.toif");
include_icon!(ICON_CHECKMARK, "layout_eckhart/res/keyboard/checkmark.toif");
include_icon!(ICON_CROSS, "layout_eckhart/res/keyboard/cross.toif");
include_icon!(
    ICON_DASH_HORIZONTAL,
    "layout_eckhart/res/keyboard/dash_horizontal.toif"
);
include_icon!(
    ICON_DASH_VERTICAL,
    "layout_eckhart/res/keyboard/dash_vertical.toif"
);
include_icon!(ICON_DELETE, "layout_eckhart/res/keyboard/delete.toif");
include_icon!(ICON_SPACE, "layout_eckhart/res/keyboard/space.toif");
include_icon!(
    ICON_SPECIAL_CHARS,
    "layout_eckhart/res/keyboard/special_chars_group.toif"
);
// Welcome screen.
include_icon!(ICON_LOGO, "layout_eckhart/res/lock_full.toif");
// Homescreen notifications.
include_icon!(ICON_WARNING40, "layout_eckhart/res/warning40.toif");

// Battery icons
include_icon!(ICON_BATTERY_BAR, "layout_eckhart/res/battery_bar.toif");
include_icon!(ICON_BATTERY_ZAP, "layout_eckhart/res/battery_zap.toif");

// Border overlay icons for bootloader screens and hold to confirm animation
include_icon!(ICON_BORDER_BL, "layout_eckhart/res/border/BL.toif");
include_icon!(ICON_BORDER_BR, "layout_eckhart/res/border/BR.toif");
include_icon!(ICON_BORDER_TL, "layout_eckhart/res/border/TL.toif");
include_icon!(ICON_BORDER_TR, "layout_eckhart/res/border/TR.toif");

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
    GREY_EXTRA_LIGHT,
    BG,
    GREY_EXTRA_LIGHT,
    GREY_EXTRA_LIGHT,
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
/// Roboto Mono Light - 30 (Address, data)
pub const TEXT_MONO_LIGHT: TextStyle = TextStyle::new(
    fonts::FONT_MONO_LIGHT_30,
    GREY_EXTRA_LIGHT,
    BG,
    GREY_EXTRA_LIGHT,
    GREY_EXTRA_LIGHT,
);

/// Decide the text style of chunkified text according to its length.
pub fn get_chunkified_text_style(_character_length: usize) -> &'static TextStyle {
    // TODO: implement properly for Eckhart, see Delizia implemenation
    &TEXT_MONO_MEDIUM
}

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

// Button styles
pub const fn button_default() -> ButtonStyleSheet {
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
            button_color: GREY_DARK,
            icon_color: GREY_LIGHT,
            background_color: GREY_DARK,
        },
    }
}

pub const fn button_confirm() -> ButtonStyleSheet {
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
            text_color: GREEN,
            button_color: GREY_SUPER_DARK,
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

pub const fn menu_item_title_red() -> ButtonStyleSheet {
    menu_item_title!(RED)
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

// Result  constants
pub const RESULT_PADDING: i16 = 6;
pub const RESULT_FOOTER_START: i16 = 171;
pub const RESULT_FOOTER_HEIGHT: i16 = 62;
pub const RESULT_ERROR: ResultStyle =
    ResultStyle::new(FG, FATAL_ERROR_COLOR, FATAL_ERROR_HIGHLIGHT_COLOR);
