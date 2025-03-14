pub mod bootloader;

pub mod backlight;

use crate::{
    time::Duration,
    ui::{
        component::{
            text::{layout::Chunks, LineBreaking, PageBreaking, TextStyle},
            FixedHeightBar,
        },
        display::Color,
        geometry::{Insets, Offset},
        util::include_icon,
    },
};

use super::{
    component::{ButtonStyle, ButtonStyleSheet, LoaderStyle, LoaderStyleSheet, ResultStyle},
    fonts,
};

pub const ERASE_HOLD_DURATION: Duration = Duration::from_millis(1500);

// Color palette.
pub const WHITE: Color = Color::rgb(0xFF, 0xFF, 0xFF);
pub const BLACK: Color = Color::rgb(0, 0, 0);
pub const FG: Color = WHITE; // Default foreground (text & icon) color.
pub const BG: Color = BLACK; // Default background color.
pub const GREY_EXTRA_DARK: Color = Color::rgb(0x16, 0x1F, 0x24);
pub const GREY_DARK: Color = Color::rgb(0x46, 0x48, 0x4A);
pub const GREY: Color = Color::rgb(0x8B, 0x8F, 0x93); // secondary text, subtitle, instructions
pub const GREY_LIGHT: Color = Color::rgb(0xC7, 0xCD, 0xD3); // content
pub const GREY_EXTRA_LIGHT: Color = Color::rgb(0xF0, 0xF0, 0xF0); // primary text, header
pub const GREEN_DARK: Color = Color::rgb(0x06, 0x1E, 0x19);
pub const GREEN: Color = Color::rgb(0x08, 0x74, 0x48);
pub const GREEN_LIGHT: Color = Color::rgb(0x0B, 0xA5, 0x67);
pub const GREEN_LIME: Color = Color::rgb(0x9B, 0xE8, 0x87);
pub const ORANGE_DARK: Color = Color::rgb(0x18, 0x0C, 0x0A);
pub const ORANGE_DIMMED: Color = Color::rgb(0x9E, 0x57, 0x42);
pub const ORANGE_LIGHT: Color = Color::rgb(0xFF, 0x8D, 0x6A); // cancel button

pub const FATAL_ERROR_COLOR: Color = Color::rgb(0xE7, 0x0E, 0x0E);
pub const FATAL_ERROR_HIGHLIGHT_COLOR: Color = Color::rgb(0xFF, 0x41, 0x41);

// Commonly used corner radius (i.e. for buttons).
pub const RADIUS: u8 = 0;

// UI icons (white color).
// 12x12
include_icon!(ICON_FORESLASH, "layout_delizia/res/foreslash12.toif");

// 20x20
include_icon!(
    ICON_BULLET_CHECKMARK,
    "layout_delizia/res/bullet_checkmark20.toif"
);
include_icon!(ICON_PAGE_DOWN, "layout_delizia/res/page_down20.toif");
include_icon!(ICON_PAGE_UP, "layout_delizia/res/page_up20.toif");

// 24x24
include_icon!(ICON_CANCEL, "layout_delizia/res/cancel24.toif");
include_icon!(ICON_CHEVRON_LEFT, "layout_delizia/res/chevron_left24.toif");
include_icon!(
    ICON_CHEVRON_RIGHT,
    "layout_delizia/res/chevron_right24.toif"
);
include_icon!(ICON_DOWNLOAD, "layout_delizia/res/download24.toif");
include_icon!(ICON_KEY, "layout_delizia/res/key20.toif");
include_icon!(ICON_QR_CODE, "layout_delizia/res/qr_code24.toif");
include_icon!(ICON_REBOOT, "layout_delizia/res/reboot24.toif");
include_icon!(ICON_WARNING, "layout_delizia/res/warning24.toif");
include_icon!(
    ICON_SIMPLE_CHECKMARK24,
    "layout_delizia/res/simple_checkmark24.toif"
);

// 30x30
include_icon!(ICON_AUTOFILL, "layout_delizia/res/autofill30.toif");
include_icon!(ICON_CLOSE, "layout_delizia/res/close30.toif");
include_icon!(
    ICON_CONFIRM_INPUT,
    "layout_delizia/res/confirm_input30.toif"
);
include_icon!(ICON_DELETE, "layout_delizia/res/delete30.toif");
include_icon!(ICON_MENU, "layout_delizia/res/menu30.toif");
include_icon!(
    ICON_SIMPLE_CHECKMARK30,
    "layout_delizia/res/simple_checkmark30.toif"
);
include_icon!(ICON_SIGN, "layout_delizia/res/sign30.toif");

// 40x40
include_icon!(ICON_MINUS, "layout_delizia/res/minus40.toif");
include_icon!(ICON_PLUS, "layout_delizia/res/plus40.toif");

// Homescreen
include_icon!(
    ICON_LOCKSCREEN_FILTER,
    "layout_delizia/res/lockscreen_filter.toif"
);

// Scrollbar/PIN dots - taken from model T
include_icon!(DOT_ACTIVE, "layout_delizia/res/scroll-active.toif");
include_icon!(DOT_INACTIVE, "layout_delizia/res/scroll-inactive.toif");
include_icon!(
    DOT_INACTIVE_HALF,
    "layout_delizia/res/scroll-inactive-half.toif"
);
include_icon!(
    DOT_INACTIVE_QUARTER,
    "layout_delizia/res/scroll-inactive-quarter.toif"
);
include_icon!(DOT_SMALL, "layout_delizia/res/scroll-small.toif");
include_icon!(ICON_PIN_BULLET, "layout_delizia/res/pin_bullet6.toif");

// Text arrows.
include_icon!(ICON_PAGE_NEXT, "layout_delizia/res/page-next.toif");
include_icon!(ICON_PAGE_PREV, "layout_delizia/res/page-prev.toif");

// Icon for "<space>*#" key on the passphrase keyboard.
include_icon!(
    ICON_SPECIAL_CHARS_GROUP,
    "layout_delizia/res/special_chars_group.toif"
);
// Icon for "next keyboard layout" for special characters
include_icon!(ICON_ASTERISK, "layout_delizia/res/asterisk16.toif");

// Welcome screen.
include_icon!(ICON_LOGO, "layout_delizia/res/lock_full.toif");

// Homescreen notifications.
include_icon!(ICON_WARNING40, "layout_delizia/res/warning40.toif");

// Default homescreen
include_icon!(HOMESCREEN_ICON, "layout_delizia/res/hs_lock.toif");

pub const fn label_default() -> TextStyle {
    TEXT_NORMAL
}

pub const fn label_keyboard() -> TextStyle {
    TextStyle::new(
        fonts::FONT_DEMIBOLD,
        GREY_EXTRA_LIGHT,
        BG,
        GREY_LIGHT,
        GREY_LIGHT,
    )
}

pub const fn label_keyboard_prompt() -> TextStyle {
    TextStyle::new(fonts::FONT_DEMIBOLD, GREY_LIGHT, BG, GREY_LIGHT, GREY_LIGHT)
}

pub const fn label_keyboard_warning() -> TextStyle {
    TextStyle::new(
        fonts::FONT_DEMIBOLD,
        ORANGE_LIGHT,
        BG,
        GREY_LIGHT,
        GREY_LIGHT,
    )
}

pub const fn label_keyboard_minor() -> TextStyle {
    TEXT_NORMAL_GREY_EXTRA_LIGHT
}

pub const fn label_warning() -> TextStyle {
    TEXT_DEMIBOLD
}

pub const fn label_warning_value() -> TextStyle {
    TEXT_NORMAL_GREY_EXTRA_LIGHT
}

pub const fn label_recovery_title() -> TextStyle {
    TEXT_BOLD
}

pub const fn label_recovery_description() -> TextStyle {
    TEXT_NORMAL_GREY_EXTRA_LIGHT
}

pub const fn label_progress() -> TextStyle {
    TEXT_BOLD
}

pub const fn label_title_main() -> TextStyle {
    TextStyle::new(
        fonts::FONT_DEMIBOLD,
        GREY_EXTRA_LIGHT,
        GREY_DARK,
        GREY_LIGHT,
        GREY_LIGHT,
    )
}

pub const fn label_title_danger() -> TextStyle {
    TextStyle::new(
        fonts::FONT_DEMIBOLD,
        ORANGE_LIGHT,
        GREY_DARK,
        GREY_LIGHT,
        GREY_LIGHT,
    )
}

pub const fn label_title_sub() -> TextStyle {
    TextStyle::new(fonts::FONT_SUB, GREY, GREY_DARK, GREY_LIGHT, GREY_LIGHT)
}

pub const fn label_coinjoin_progress() -> TextStyle {
    TextStyle::new(fonts::FONT_DEMIBOLD, FG, ORANGE_DIMMED, FG, FG)
}

pub const fn button_default() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREY_LIGHT,
            button_color: BG,
            icon_color: GREY,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREY_EXTRA_LIGHT,
            button_color: BG,
            icon_color: GREY_EXTRA_LIGHT,
            background_color: BG,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREY_LIGHT,
            button_color: BG,
            icon_color: GREY_LIGHT,
            background_color: BG,
        },
    }
}

pub const fn button_warning_high() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: ORANGE_LIGHT,
            button_color: BG,
            icon_color: ORANGE_DIMMED,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: ORANGE_LIGHT,
            button_color: BG,
            icon_color: ORANGE_DIMMED,
            background_color: BG,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: ORANGE_LIGHT,
            button_color: BG,
            icon_color: ORANGE_DIMMED,
            background_color: BG,
        },
    }
}

pub const fn button_warning_low() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREY_LIGHT,
            button_color: BG,
            icon_color: GREEN_LIME,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREY_LIGHT,
            button_color: BG,
            icon_color: GREEN_LIME,
            background_color: BG,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREY_LIGHT,
            button_color: BG,
            icon_color: GREEN_LIME,
            background_color: BG,
        },
    }
}

// TODO: somehow merge with button_passphrase_confirm?
pub const fn button_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREEN_LIME,
            button_color: GREEN_DARK,
            icon_color: GREEN_LIME,
            background_color: GREEN_DARK,
        },
        active: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREEN_LIME,
            button_color: GREEN_LIGHT,
            icon_color: GREEN_DARK,
            background_color: GREEN_LIGHT,
        },
        // not used
        disabled: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: BG,
            button_color: BG,
            icon_color: BG,
            background_color: BG,
        },
    }
}

pub const fn button_cancel() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: ORANGE_LIGHT,
            button_color: ORANGE_DARK,
            icon_color: ORANGE_LIGHT,
            background_color: GREEN_DARK,
        },
        active: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: ORANGE_DARK,
            button_color: ORANGE_LIGHT,
            icon_color: ORANGE_DARK,
            background_color: ORANGE_LIGHT,
        },
        // not used
        disabled: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: BG,
            button_color: BG,
            icon_color: BG,
            background_color: BG,
        },
    }
}

pub const fn button_danger() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: ORANGE_LIGHT,
            button_color: BG,
            icon_color: ORANGE_DIMMED,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: ORANGE_LIGHT,
            button_color: BG,
            icon_color: ORANGE_LIGHT,
            background_color: BG,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: ORANGE_LIGHT,
            button_color: BG,
            icon_color: ORANGE_LIGHT,
            background_color: BG,
        },
    }
}

// used for PIN digit keys and passphrase/recovery letter keys
pub const fn button_keyboard() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREY_LIGHT,
            button_color: GREY_EXTRA_DARK,
            icon_color: GREY_LIGHT,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: BG,
            button_color: GREY_LIGHT,
            icon_color: BG,
            background_color: BG,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREY_DARK,
            button_color: BG, // so there is no "button" itself, just the text
            icon_color: GREY_LIGHT,
            background_color: BG,
        },
    }
}

pub const fn button_keyboard_cancel() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_MONO,
            text_color: FG,
            button_color: BG, // TODO: gradient
            icon_color: ORANGE_LIGHT,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_MONO,
            text_color: FG,
            button_color: ORANGE_LIGHT,
            icon_color: BG,
            background_color: BG,
        },
        // not used
        disabled: &ButtonStyle {
            font: fonts::FONT_MONO,
            text_color: FG,
            button_color: BG,
            icon_color: GREEN_LIGHT,
            background_color: BG,
        },
    }
}

pub const fn button_keyboard_erase() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_MONO,
            text_color: FG,
            button_color: BG, // TODO: gradient
            icon_color: GREY,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_MONO,
            text_color: FG,
            button_color: GREY_LIGHT,
            icon_color: BG,
            background_color: BG,
        },
        // not used
        disabled: &ButtonStyle {
            font: fonts::FONT_MONO,
            text_color: FG,
            button_color: BG,
            icon_color: GREEN_LIGHT,
            background_color: BG,
        },
    }
}

// TODO: merge `button_pin_confirm` and `_passphrase_confirm`. Need to render
// button `.with_radius` correctly
pub const fn button_pin_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_MONO,
            text_color: FG,
            button_color: GREEN_DARK,
            icon_color: GREEN_LIME,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_MONO,
            text_color: FG,
            button_color: GREEN_LIGHT,
            icon_color: GREEN_DARK,
            background_color: BG,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_MONO,
            text_color: GREY_DARK,
            button_color: BG,
            icon_color: GREY_DARK,
            background_color: BG,
        },
    }
}

pub const fn button_passphrase_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREEN_LIME,
            button_color: GREEN_LIGHT,
            icon_color: GREEN_LIME,
            background_color: GREEN_DARK,
        },
        active: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREEN_LIME,
            button_color: GREEN_LIGHT,
            icon_color: GREEN_DARK,
            background_color: GREEN_LIGHT,
        },
        // not used
        disabled: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: BG,
            button_color: BG,
            icon_color: BG,
            background_color: BG,
        },
    }
}

pub const fn button_passphrase_confirm_empty() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREY,
            button_color: GREY_EXTRA_DARK,
            icon_color: GREY,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: BG,
            button_color: GREY_LIGHT,
            icon_color: BG,
            background_color: GREY_LIGHT,
        },
        // not used
        disabled: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: BG,
            button_color: BG,
            icon_color: BG,
            background_color: BG,
        },
    }
}

pub const fn button_passphrase_next() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREY_LIGHT,
            button_color: BG, // TODO: gradient
            icon_color: GREY_LIGHT,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREY_LIGHT,
            button_color: BG, // TODO: gradient
            icon_color: GREY_LIGHT,
            background_color: BG,
        },
        // not used
        disabled: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREY_LIGHT,
            button_color: BG,
            icon_color: GREY_LIGHT,
            background_color: BG,
        },
    }
}

pub const fn button_recovery_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREEN_LIME,
            button_color: GREEN_LIGHT,
            icon_color: GREEN_LIME,
            background_color: GREEN_DARK,
        },
        active: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREEN_DARK,
            button_color: GREEN_LIGHT,
            icon_color: GREEN_DARK,
            background_color: GREEN_LIGHT,
        },
        // used in SLIP-39 recovery for "*"
        disabled: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREY_LIGHT,
            button_color: BG,
            icon_color: BG,
            background_color: BG,
        },
    }
}

pub const fn button_suggestion_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREY_LIGHT, // difference
            button_color: GREEN_LIGHT,
            icon_color: GREEN_LIME,
            background_color: GREEN_DARK,
        },
        active: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREEN_LIME,
            button_color: GREEN_LIGHT,
            icon_color: GREEN_DARK,
            background_color: GREEN_LIGHT,
        },
        // not used
        disabled: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: BG,
            button_color: BG,
            icon_color: BG,
            background_color: BG,
        },
    }
}

pub const fn button_recovery_autocomplete() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREY_LIGHT,
            button_color: GREY_EXTRA_DARK,
            icon_color: GREY_LIGHT,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: BG,
            button_color: FG,
            icon_color: BG,
            background_color: FG,
        },
        // not used
        disabled: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: BG,
            button_color: BG,
            icon_color: BG,
            background_color: BG,
        },
    }
}

pub const fn button_suggestion_autocomplete() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREY,
            button_color: BG,
            icon_color: BG,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_MONO,
            text_color: BG,
            button_color: FG,
            icon_color: BG,
            background_color: FG,
        },
        // not used
        disabled: &ButtonStyle {
            font: fonts::FONT_MONO,
            text_color: BG,
            button_color: BG,
            icon_color: BG,
            background_color: BG,
        },
    }
}

pub const fn button_counter() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREY,
            button_color: GREY_EXTRA_DARK,
            icon_color: GREY,
            background_color: BG,
        },
        active: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: BG,
            button_color: GREY_LIGHT,
            icon_color: BG,
            background_color: BG,
        },
        disabled: &ButtonStyle {
            font: fonts::FONT_DEMIBOLD,
            text_color: GREY_DARK,
            button_color: BG,
            icon_color: GREY_DARK,
            background_color: BG,
        },
    }
}

pub const fn button_clear() -> ButtonStyleSheet {
    button_default()
}

pub const fn loader_default() -> LoaderStyleSheet {
    LoaderStyleSheet {
        active: &LoaderStyle {
            icon: None,
            active: GREEN_LIGHT,
            inactive: GREY_EXTRA_DARK,
            background_color: BG,
        },
    }
}

pub const fn loader_lock_icon() -> LoaderStyleSheet {
    LoaderStyleSheet {
        active: &LoaderStyle {
            icon: Some((ICON_KEY, FG)),
            active: GREEN_LIGHT,
            inactive: GREY_EXTRA_DARK,
            background_color: BG,
        },
    }
}

pub const TEXT_SUPER: TextStyle = TextStyle::new(fonts::FONT_BIG, GREY_EXTRA_LIGHT, BG, GREY, GREY);
pub const TEXT_MAIN_GREY_EXTRA_LIGHT: TextStyle =
    TextStyle::new(fonts::FONT_DEMIBOLD, GREY_EXTRA_LIGHT, BG, GREY, GREY);
pub const TEXT_MAIN_GREY_LIGHT: TextStyle =
    TextStyle::new(fonts::FONT_DEMIBOLD, GREY_LIGHT, BG, GREY, GREY);
pub const TEXT_SUB_GREY_LIGHT: TextStyle =
    TextStyle::new(fonts::FONT_SUB, GREY_LIGHT, BG, GREY, GREY);
pub const TEXT_SUB_GREY: TextStyle = TextStyle::new(fonts::FONT_SUB, GREY, BG, GREY, GREY);
pub const TEXT_SUB_GREEN_LIME: TextStyle =
    TextStyle::new(fonts::FONT_SUB, GREEN_LIME, BG, GREEN_LIME, GREEN_LIME);
pub const TEXT_WARNING: TextStyle =
    TextStyle::new(fonts::FONT_DEMIBOLD, ORANGE_LIGHT, BG, GREY, GREY);
pub const TEXT_MONO: TextStyle = TextStyle::new(fonts::FONT_MONO, GREY_EXTRA_LIGHT, BG, GREY, GREY)
    .with_line_breaking(LineBreaking::BreakWordsNoHyphen)
    .with_page_breaking(PageBreaking::CutAndInsertEllipsisBoth)
    .with_ellipsis_icon(ICON_PAGE_NEXT, 0)
    .with_prev_page_icon(ICON_PAGE_PREV, 0);
pub const TEXT_MONO_WITH_CLASSIC_ELLIPSIS: TextStyle =
    TextStyle::new(fonts::FONT_MONO, GREY_EXTRA_LIGHT, BG, GREY, GREY)
        .with_line_breaking(LineBreaking::BreakWordsNoHyphen)
        .with_page_breaking(PageBreaking::CutAndInsertEllipsisBoth)
        .with_prev_page_icon(ICON_PAGE_PREV, 0);
pub const TEXT_MONO_GREY_LIGHT: TextStyle = TextStyle {
    text_color: GREY_LIGHT,
    ..TEXT_MONO
};
/// Makes sure that the displayed text (usually address) will get divided into
/// smaller chunks.
pub const TEXT_MONO_ADDRESS_CHUNKS: TextStyle = TEXT_MONO_GREY_LIGHT
    .with_chunks(Chunks::new(4, 9))
    .with_line_spacing(5);
/// Smaller horizontal chunk offset, used e.g. for long Cardano addresses.
/// Also moving the next page ellipsis to the left (as there is a space on the
/// left). Last but not least, maximum number of rows is 4 in this case.
pub const TEXT_MONO_ADDRESS_CHUNKS_SMALLER_X_OFFSET: TextStyle = TEXT_MONO_GREY_LIGHT
    .with_chunks(Chunks::new(4, 7).with_max_rows(4))
    .with_line_spacing(5)
    .with_ellipsis_icon(ICON_PAGE_NEXT, -12);

// TODO: remove TextStyles below when ui-t3t1 done
pub const TEXT_NORMAL: TextStyle =
    TextStyle::new(fonts::FONT_DEMIBOLD, FG, BG, GREY_LIGHT, GREY_LIGHT);
pub const TEXT_DEMIBOLD: TextStyle =
    TextStyle::new(fonts::FONT_DEMIBOLD, FG, BG, GREY_LIGHT, GREY_LIGHT);
pub const TEXT_BOLD: TextStyle =
    TextStyle::new(fonts::FONT_DEMIBOLD, FG, BG, GREY_LIGHT, GREY_LIGHT);

/// Decide the text style of chunkified text according to its length.
pub fn get_chunkified_text_style(character_length: usize) -> &'static TextStyle {
    // Longer addresses have smaller x_offset so they fit even with scrollbar
    // (as they will be shown on more than one page)
    const FITS_ON_ONE_PAGE: usize = 16 * 4;
    if character_length <= FITS_ON_ONE_PAGE {
        &TEXT_MONO_ADDRESS_CHUNKS
    } else {
        &TEXT_MONO_ADDRESS_CHUNKS_SMALLER_X_OFFSET
    }
}

pub const TEXT_NORMAL_GREY_EXTRA_LIGHT: TextStyle = TextStyle::new(
    fonts::FONT_DEMIBOLD,
    GREY_EXTRA_LIGHT,
    BG,
    GREY_LIGHT,
    GREY_LIGHT,
);
pub const TEXT_CHECKLIST_DEFAULT: TextStyle = TextStyle::new(fonts::FONT_SUB, GREY, BG, GREY, GREY);
pub const TEXT_CHECKLIST_SELECTED: TextStyle =
    TextStyle::new(fonts::FONT_DEMIBOLD, GREY_LIGHT, BG, GREY_LIGHT, GREY_LIGHT);
pub const TEXT_CHECKLIST_DONE: TextStyle = TextStyle::new(fonts::FONT_SUB, GREY, BG, GREY, GREY);

/// Spacing between components (e.g. header and main content) and offsets from
/// the side of the screen. Generally applied everywhere except the top side of
/// the header. [px]
pub const SPACING: i16 = 2;

pub const TITLE_HEIGHT: i16 = 42;
pub const CONTENT_BORDER: i16 = 0;
pub const BUTTON_HEIGHT: i16 = 62;
pub const BUTTON_WIDTH: i16 = 78;
pub const BUTTON_SPACING: i16 = SPACING;
pub const KEYBOARD_SPACING: i16 = BUTTON_SPACING;
pub const CHECKLIST_SPACING: i16 = 12;
pub const RECOVERY_SPACING: i16 = 18;
pub const CORNER_BUTTON_SIDE: i16 = 44;
pub const CORNER_BUTTON_SPACING: i16 = BUTTON_SPACING;
pub const COUNTER_BUTTON_HEIGHT: i16 = 60;
pub const INFO_BUTTON_HEIGHT: i16 = 44;
pub const PIN_BUTTON_HEIGHT: i16 = 52;
pub const MNEMONIC_BUTTON_HEIGHT: i16 = 62;
pub const PASSPHRASE_BUTTON_HEIGHT: i16 = 48;
pub const RESULT_PADDING: i16 = 6;
pub const RESULT_FOOTER_START: i16 = 171;
pub const RESULT_FOOTER_HEIGHT: i16 = 62;
pub const DETAILS_SPACING: i16 = 8;

// checklist settings
pub const CHECKLIST_CHECK_WIDTH: i16 = 32; // icon width (20px) + padding (12px)
pub const CHECKLIST_DONE_OFFSET: Offset = Offset::y(-2);

pub const fn button_bar<T>(inner: T) -> FixedHeightBar<T> {
    FixedHeightBar::bottom(inner, BUTTON_HEIGHT)
}

/// +----------+
/// |     6    |
/// |  +----+  |
/// | 6|    | 6|
/// |  +----+  |
/// |     6    |
/// +----------+
pub const fn borders() -> Insets {
    Insets::new(0, 0, 0, 0)
}

pub const fn borders_notification() -> Insets {
    Insets::new(42, 0, 0, 0)
}

pub const RESULT_ERROR: ResultStyle =
    ResultStyle::new(FG, FATAL_ERROR_COLOR, FATAL_ERROR_HIGHLIGHT_COLOR);
