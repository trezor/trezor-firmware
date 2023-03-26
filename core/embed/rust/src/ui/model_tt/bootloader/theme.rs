use crate::{
    alpha,
    ui::{
        component::{text::TextStyle, LineBreaking::BreakWordsNoHyphen},
        constant::WIDTH,
        display::{Color, Font},
        geometry::{Offset, Point, Rect},
        model_tt::{
            component::{ButtonStyle, ButtonStyleSheet},
            theme::{BLACK, FG, GREY_DARK, GREY_LIGHT, GREY_MEDIUM, WHITE},
        },
    },
};

pub const BLD_BG: Color = Color::rgb(0x00, 0x17, 0xA3);
pub const BLD_FG: Color = WHITE;
pub const BLD_WIPE_COLOR: Color = Color::rgb(0xAD, 0x2B, 0x2B);
pub const BLD_WIPE_TEXT_COLOR: Color = Color::rgb(0xD6, 0x95, 0x95);

pub const BLD_WIPE_BTN_COLOR: Color = Color::alpha(BLD_WIPE_COLOR, alpha!(0.3));
pub const BLD_WIPE_BTN_COLOR_ACTIVE: Color = Color::rgb(0xB9, 0x4B, 0x4B);
pub const BLD_WIPE_CANCEL_BTN_COLOR_ACTIVE: Color = Color::rgb(0xF3, 0xDF, 0xDF);

pub const BLD_INSTALL_BTN_COLOR: Color = Color::alpha(BLD_BG, alpha!(0.3));
pub const BLD_INSTALL_BTN_COLOR_ACTIVE: Color = Color::rgb(0xD9, 0xDC, 0xF1);
pub const BLD_INSTALL_CANCEL_BTN_COLOR_ACTIVE: Color = Color::rgb(0x26, 0x3A, 0xB1);

pub const BLD_COLOR_SUBMSG: Color = Color::rgb(0x80, 0x8B, 0xD1);

pub const BLD_BTN_MENU_COLOR: Color = Color::alpha(BLD_BG, alpha!(0.22));
pub const BLD_BTN_MENU_COLOR_ACTIVE: Color = Color::alpha(BLD_BG, alpha!(0.11));
pub const BLD_BTN_MENUITEM_COLOR: Color = Color::alpha(BLD_BG, alpha!(0.33));
pub const BLD_BTN_MENUITEM_COLOR_ACTIVE: Color =
    Color::rgba(BLD_BG, 0xFF, 0xFF, 0xFF, alpha!(0.11));
pub const BLD_TITLE_COLOR: Color = Color::rgba(BLD_BG, 0xFF, 0xFF, 0xFF, alpha!(0.75));

pub const WELCOME_COLOR: Color = BLACK;

// Commonly used corner radius (i.e. for buttons).
pub const RADIUS: u8 = 2;

// Commonly used constants for UI elements.
pub const CONTENT_PADDING: i16 = 10;
pub const TITLE_AREA: Rect = Rect::new(Point::new(15, 14), Point::new(200, 30));
pub const CORNER_BUTTON_SIZE: i16 = 32;
pub const CORNER_BUTTON_PADDING: i16 = 8;
pub const CORNER_BUTTON_AREA: Rect = Rect::from_top_left_and_size(
    Point::new(
        WIDTH - CORNER_BUTTON_SIZE - CORNER_BUTTON_PADDING,
        CORNER_BUTTON_PADDING,
    ),
    Offset::uniform(CORNER_BUTTON_SIZE),
);
pub const TITLE_AREA_HEIGHT: i16 = 16;
pub const TITLE_AREA_START_Y: i16 = 8;
pub const BUTTON_AREA_START: i16 = 188;

// UI icons.
pub const ICON_CANCEL: &[u8] = include_res!("model_tt/res/x24.toif");
pub const ICON_CONFIRM: &[u8] = include_res!("model_tt/res/check24.toif");

// BLD icons
pub const CLOSE: &[u8] = include_res!("model_tt/res/close.toif");
pub const ERASE: &[u8] = include_res!("model_tt/res/erase.toif");
pub const ERASE_BIG: &[u8] = include_res!("model_tt/res/erase_big.toif");
pub const REBOOT: &[u8] = include_res!("model_tt/res/reboot.toif");
pub const MENU: &[u8] = include_res!("model_tt/res/menu.toif");
pub const RECEIVE: &[u8] = include_res!("model_tt/res/receive.toif");
pub const LOGO_EMPTY: &[u8] = include_res!("model_tt/res/trezor_empty.toif");
pub const INFO_SMALL: &[u8] = include_res!("model_tt/res/info_small.toif");

pub fn button_install_cancel() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::BOLD,
            text_color: WHITE,
            button_color: BLD_BTN_MENUITEM_COLOR,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: Font::BOLD,
            text_color: WHITE,
            button_color: BLD_INSTALL_CANCEL_BTN_COLOR_ACTIVE,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: Font::BOLD,
            text_color: GREY_LIGHT,
            button_color: GREY_DARK,
            background_color: WHITE,
            border_color: WHITE,
            border_radius: RADIUS,
            border_width: 0,
        },
    }
}

pub fn button_install_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::BOLD,
            text_color: BLD_BG,
            button_color: WHITE,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: Font::BOLD,
            text_color: BLD_BG,
            button_color: BLD_INSTALL_BTN_COLOR_ACTIVE,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: Font::BOLD,
            text_color: FG,
            button_color: GREY_DARK,
            background_color: FG,
            border_color: FG,
            border_radius: RADIUS,
            border_width: 0,
        },
    }
}

pub fn button_wipe_cancel() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::BOLD,
            text_color: BLD_WIPE_COLOR,
            button_color: WHITE,
            background_color: BLD_WIPE_COLOR,
            border_color: BLD_WIPE_COLOR,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: Font::BOLD,
            text_color: BLD_WIPE_COLOR,
            button_color: BLD_WIPE_CANCEL_BTN_COLOR_ACTIVE,
            background_color: BLD_WIPE_COLOR,
            border_color: BLD_WIPE_COLOR,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: Font::BOLD,
            text_color: GREY_LIGHT,
            button_color: GREY_DARK,
            background_color: WHITE,
            border_color: WHITE,
            border_radius: RADIUS,
            border_width: 0,
        },
    }
}

pub fn button_wipe_confirm() -> ButtonStyleSheet {
    ButtonStyleSheet {
        normal: &ButtonStyle {
            font: Font::BOLD,
            text_color: WHITE,
            button_color: BLD_WIPE_BTN_COLOR,
            background_color: BLD_WIPE_COLOR,
            border_color: BLD_WIPE_COLOR,
            border_radius: RADIUS,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: Font::BOLD,
            text_color: WHITE,
            button_color: BLD_WIPE_BTN_COLOR_ACTIVE,
            background_color: BLD_WIPE_COLOR,
            border_color: BLD_WIPE_COLOR,
            border_radius: RADIUS,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: Font::BOLD,
            text_color: FG,
            button_color: GREY_DARK,
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
            font: Font::BOLD,
            text_color: BLD_FG,
            button_color: BLD_BTN_MENU_COLOR,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: 4,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: Font::BOLD,
            text_color: BLD_FG,
            button_color: BLD_BTN_MENU_COLOR_ACTIVE,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: 4,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: Font::BOLD,
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
            font: Font::BOLD,
            text_color: BLD_FG,
            button_color: BLD_BTN_MENUITEM_COLOR,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: 4,
            border_width: 0,
        },
        active: &ButtonStyle {
            font: Font::BOLD,
            text_color: BLD_FG,
            button_color: BLD_BTN_MENUITEM_COLOR_ACTIVE,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: 4,
            border_width: 0,
        },
        disabled: &ButtonStyle {
            font: Font::BOLD,
            text_color: GREY_LIGHT,
            button_color: BLD_BTN_MENUITEM_COLOR,
            background_color: BLD_BG,
            border_color: BLD_BG,
            border_radius: 4,
            border_width: 0,
        },
    }
}
pub const TEXT_WELCOME: TextStyle = TextStyle::new(
    Font::NORMAL,
    GREY_MEDIUM,
    WELCOME_COLOR,
    GREY_MEDIUM,
    GREY_MEDIUM,
);
pub const TEXT_WELCOME_BOLD: TextStyle = TextStyle::new(Font::BOLD, FG, WELCOME_COLOR, FG, FG);
pub const TEXT_TITLE: TextStyle = TextStyle::new(
    Font::BOLD,
    BLD_TITLE_COLOR,
    BLD_BG,
    BLD_TITLE_COLOR,
    BLD_TITLE_COLOR,
);
pub const TEXT_SUBMSG_INITIAL: TextStyle = TextStyle::new(
    Font::BOLD,
    GREY_MEDIUM,
    WELCOME_COLOR,
    GREY_MEDIUM,
    GREY_MEDIUM,
);

pub const TEXT_NORMAL: TextStyle = TextStyle::new(Font::NORMAL, BLD_FG, BLD_BG, BLD_FG, BLD_FG);
pub const TEXT_FINGERPRINT: TextStyle =
    TextStyle::new(Font::NORMAL, BLD_FG, BLD_BG, BLD_FG, BLD_FG)
        .with_line_breaking(BreakWordsNoHyphen);
pub const TEXT_BOLD: TextStyle = TextStyle::new(Font::BOLD, BLD_FG, BLD_BG, BLD_FG, BLD_FG);
pub const TEXT_WIPE_BOLD: TextStyle = TextStyle::new(
    Font::BOLD,
    BLD_WIPE_TEXT_COLOR,
    BLD_WIPE_COLOR,
    BLD_WIPE_TEXT_COLOR,
    BLD_WIPE_TEXT_COLOR,
);
pub const TEXT_SUBMSG: TextStyle = TextStyle::new(
    Font::BOLD,
    BLD_COLOR_SUBMSG,
    BLD_BG,
    BLD_COLOR_SUBMSG,
    BLD_COLOR_SUBMSG,
);
