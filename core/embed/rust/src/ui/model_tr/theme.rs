use crate::ui::{
    component::text::{formatted::FormattedFonts, TextStyle},
    display::{Color, Font, IconAndName},
};

// Color palette.
pub const FG: Color = Color::white(); // Default foreground (text & icon) color.
pub const BG: Color = Color::black(); // Default background color.

// Font constants.
pub const FONT_BUTTON: Font = Font::MONO;
pub const FONT_HEADER: Font = Font::BOLD;
pub const FONT_CHOICE_ITEMS: Font = Font::NORMAL;

// Text constants.
pub const TEXT_NORMAL: TextStyle =
    TextStyle::new(Font::NORMAL, FG, BG, FG, FG).with_ellipsis_icon(ICON_NEXT_PAGE.0);
pub const TEXT_DEMIBOLD: TextStyle =
    TextStyle::new(Font::DEMIBOLD, FG, BG, FG, FG).with_ellipsis_icon(ICON_NEXT_PAGE.0);
pub const TEXT_BOLD: TextStyle =
    TextStyle::new(Font::BOLD, FG, BG, FG, FG).with_ellipsis_icon(ICON_NEXT_PAGE.0);
pub const TEXT_MONO: TextStyle =
    TextStyle::new(Font::MONO, FG, BG, FG, FG).with_ellipsis_icon(ICON_NEXT_PAGE.0);
// Header does not have the ellipsis
pub const TEXT_HEADER: TextStyle = TextStyle::new(Font::BOLD, FG, BG, FG, FG);

pub const FORMATTED: FormattedFonts = FormattedFonts {
    normal: Font::NORMAL,
    demibold: Font::DEMIBOLD,
    bold: Font::BOLD,
    mono: Font::MONO,
};

// Icons with their names for debugging purposes
pub const ICON_ARM_LEFT: IconAndName =
    IconAndName::new(include_res!("model_tr/res/arm_left.toif"), "arm_left"); // 6*10
pub const ICON_ARM_RIGHT: IconAndName =
    IconAndName::new(include_res!("model_tr/res/arm_right.toif"), "arm_right"); // 6*10
pub const ICON_ARROW_LEFT: IconAndName =
    IconAndName::new(include_res!("model_tr/res/arrow_left.toif"), "arrow_left"); // 6*10
pub const ICON_ARROW_RIGHT: IconAndName =
    IconAndName::new(include_res!("model_tr/res/arrow_right.toif"), "arrow_right"); // 6*10
pub const ICON_ARROW_UP: IconAndName =
    IconAndName::new(include_res!("model_tr/res/arrow_up.toif"), "arrow_up"); // 10*6
pub const ICON_ARROW_DOWN: IconAndName =
    IconAndName::new(include_res!("model_tr/res/arrow_down.toif"), "arrow_down"); // 10*6
pub const ICON_AMOUNT: IconAndName =
    IconAndName::new(include_res!("model_tr/res/amount_smaller.toif"), "amount"); // 8*8
pub const ICON_BIN: IconAndName = IconAndName::new(include_res!("model_tr/res/bin.toif"), "bin"); // 10*10
pub const ICON_CANCEL_OUTLINE: IconAndName = IconAndName::new(
    include_res!("model_tr/res/cancel_for_outline.toif"),
    "cancel_outline",
); // 8*8
pub const ICON_CANCEL: IconAndName = IconAndName::new(
    include_res!("model_tr/res/cancel_no_outline.toif"),
    "cancel",
); // 8*8
pub const ICON_DELETE: IconAndName =
    IconAndName::new(include_res!("model_tr/res/delete.toif"), "delete"); // 12*8
pub const ICON_EYE: IconAndName =
    IconAndName::new(include_res!("model_tr/res/eye_round.toif"), "eye"); // 12*7
pub const ICON_FAIL: IconAndName = IconAndName::new(include_res!("model_tr/res/fail.toif"), "fail");
pub const ICON_LOCK: IconAndName = IconAndName::new(include_res!("model_tr/res/lock.toif"), "lock"); // 10*10
pub const ICON_NEXT_PAGE: IconAndName =
    IconAndName::new(include_res!("model_tr/res/next_page.toif"), "next_page"); // 10*8
pub const ICON_PARAM: IconAndName =
    IconAndName::new(include_res!("model_tr/res/param_smaller.toif"), "param"); // 7*8
pub const ICON_PREV_PAGE: IconAndName =
    IconAndName::new(include_res!("model_tr/res/prev_page.toif"), "prev_page"); // 8*10
pub const ICON_SUCCESS: IconAndName =
    IconAndName::new(include_res!("model_tr/res/success.toif"), "success");
pub const ICON_TICK: IconAndName = IconAndName::new(include_res!("model_tr/res/tick.toif"), "tick"); // 10*10
pub const ICON_USER: IconAndName =
    IconAndName::new(include_res!("model_tr/res/user_smaller.toif"), "user"); // 8*8
pub const ICON_WALLET: IconAndName =
    IconAndName::new(include_res!("model_tr/res/wallet.toif"), "wallet"); // 10*10
pub const ICON_WARNING: IconAndName =
    IconAndName::new(include_res!("model_tr/res/warning.toif"), "warning"); // 12*12

// Button height is constant for both text and icon buttons.
// It is a combination of content and (optional) outline/border.
// It is not possible to have icons 7*7, therefore having 8*8
// with empty LEFT column and BOTTOM row.
pub const BUTTON_CONTENT_HEIGHT: i16 = 7;
pub const BUTTON_OUTLINE: i16 = 3;
pub const BUTTON_HEIGHT: i16 = BUTTON_CONTENT_HEIGHT + 2 * BUTTON_OUTLINE;

// Full-size QR code.
pub const QR_SIDE_MAX: i16 = 64 - BUTTON_HEIGHT;
