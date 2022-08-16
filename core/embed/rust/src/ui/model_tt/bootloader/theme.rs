use crate::{
    alpha,
    ui::{
        display::{Color, Font},
        model_tt::{
            component::{ButtonStyle, ButtonStyleSheet},
            theme::{
                BLACK, FG, FONT_BOLD, FONT_MEDIUM, FONT_MONO, FONT_NORMAL, GREEN, GREEN_DARK,
                GREY_LIGHT, RED, RED_DARK, WHITE,
            },
        },
    },
};

pub const BLD_BG: Color = Color::rgb(0x00, 0x17, 0xA3);
pub const BLD_FG: Color = WHITE;
pub const BLD_BTN_MENU_COLOR: Color = Color::rgba(BLD_BG, 0xFF, 0xFF, 0xFF, alpha!(0.22));
pub const BLD_BTN_MENU_COLOR_ACTIVE: Color = Color::rgba(BLD_BG, 0xFF, 0xFF, 0xFF, alpha!(0.11));
pub const BLD_BTN_MENUITEM_COLOR: Color = Color::rgba(BLD_BG, 0xFF, 0xFF, 0xFF, alpha!(0.33));
pub const BLD_BTN_MENUITEM_COLOR_ACTIVE: Color =
    Color::rgba(BLD_BG, 0xFF, 0xFF, 0xFF, alpha!(0.11));
pub const BLD_TITLE_COLOR: Color = Color::rgba(BLD_BG, 0xFF, 0xFF, 0xFF, alpha!(0.75));

// Commonly used corner radius (i.e. for buttons).
pub const RADIUS: u8 = 2;

// Size of icons in the UI (i.e. inside buttons).
pub const ICON_SIZE: i32 = 16;

// UI icons.
pub const ICON_CANCEL: &[u8] = include_res!("model_tt/res/cancel.toif");
pub const ICON_CONFIRM: &[u8] = include_res!("model_tt/res/confirm.toif");
pub const IMAGE_BG: &[u8] = include_res!("model_tt/res/bg.toif");
pub const ICON_BG: &[u8] = include_res!("model_tt/res/homescreen_model_r.toif");
pub const IMAGE_HS: &[u8] = include_res!("model_tt/res/bg_s.toif");

// BLD icons
pub const CLOSE: &'static [u8] = include_res!("model_tt/res/close.toif");
pub const RESET: &'static [u8] = include_res!("model_tt/res/reset.toif");
pub const FWINFO: &'static [u8] = include_res!("model_tt/res/fwinfo.toif");
pub const REBOOT: &'static [u8] = include_res!("model_tt/res/reboot.toif");
pub const MENU: &'static [u8] = include_res!("model_tt/res/menu.toif");
pub const RECEIVE: &'static [u8] = include_res!("model_tt/res/receive.toif");

pub fn button_cancel() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: FONT_BOLD,
            text_color: WHITE,
            button_color: RED,
            background_color: WHITE,
            border_color: WHITE,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: FONT_BOLD,
            text_color: WHITE,
            button_color: RED_DARK,
            background_color: WHITE,
            border_color: WHITE,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: FONT_BOLD,
            text_color: GREY_LIGHT,
            button_color: RED,
            background_color: WHITE,
            border_color: WHITE,
            border_radius: RADIUS,
            border_width: 0,
        },
    }
}

pub fn button_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: FONT_BOLD,
            text_color: WHITE,
            button_color: GREEN,
            background_color: WHITE,
            border_color: WHITE,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: FONT_BOLD,
            text_color: WHITE,
            button_color: GREEN_DARK,
            background_color: WHITE,
            border_color: WHITE,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: FONT_BOLD,
            text_color: FG,
            button_color: GREEN,
            background_color: FG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
    }
}

pub fn button_bld_menu() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: FONT_BOLD,
            text_color: BLD_FG,
            button_color: BLD_BTN_MENU_COLOR,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: 4,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: FONT_BOLD,
            text_color: BLD_FG,
            button_color: BLD_BTN_MENU_COLOR_ACTIVE,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: 4,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: FONT_BOLD,
            text_color: GREY_LIGHT,
            button_color: BLD_BTN_MENU_COLOR,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: 4,
            border_width: 0,
        },
    }
}

pub fn button_bld_menu_item() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: FONT_BOLD,
            text_color: BLD_FG,
            button_color: BLD_BTN_MENUITEM_COLOR,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: 4,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: FONT_BOLD,
            text_color: BLD_FG,
            button_color: BLD_BTN_MENUITEM_COLOR_ACTIVE,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: 4,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: FONT_BOLD,
            text_color: GREY_LIGHT,
            button_color: BLD_BTN_MENUITEM_COLOR,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: 4,
            border_width: 0,
        },
    }
}
//
// pub struct TTBootloaderTextTemp;
// //because old style confirm screen
// impl DefaultTextTheme for TTBootloaderTextTemp {
//     const BACKGROUND_COLOR: Color = WHITE;
//     const TEXT_FONT: Font = FONT_NORMAL;
//     const TEXT_COLOR: Color = BLACK;
//     const HYPHEN_FONT: Font = FONT_BOLD;
//     const HYPHEN_COLOR: Color = GREY_LIGHT;
//     const ELLIPSIS_FONT: Font = FONT_BOLD;
//     const ELLIPSIS_COLOR: Color = GREY_LIGHT;
//
//     const NORMAL_FONT: Font = FONT_NORMAL;
//     const MEDIUM_FONT: Font = FONT_MEDIUM;
//     const BOLD_FONT: Font = FONT_BOLD;
//     const MONO_FONT: Font = FONT_MONO;
// }
//
// pub struct TTBootloaderText;
// impl DefaultTextTheme for TTBootloaderText {
//     const BACKGROUND_COLOR: Color = BLD_BG;
//     const TEXT_FONT: Font = FONT_MEDIUM;
//     const TEXT_COLOR: Color = BLD_FG;
//     const HYPHEN_FONT: Font = FONT_BOLD;
//     const HYPHEN_COLOR: Color = GREY_LIGHT;
//     const ELLIPSIS_FONT: Font = FONT_BOLD;
//     const ELLIPSIS_COLOR: Color = GREY_LIGHT;
//
//     const NORMAL_FONT: Font = FONT_NORMAL;
//     const MEDIUM_FONT: Font = FONT_MEDIUM;
//     const BOLD_FONT: Font = FONT_BOLD;
//     const MONO_FONT: Font = FONT_MONO;
// }
