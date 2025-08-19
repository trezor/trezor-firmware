#[cfg(feature = "micropython")]
pub mod background;
pub mod backlight;
#[cfg(any(feature = "bootloader", feature = "prodtest"))]
pub mod bootloader;
#[cfg(feature = "micropython")]
pub mod firmware;
pub mod gradient;
#[cfg(feature = "micropython")]
pub use firmware::*;

use crate::ui::{
    component::text::TextStyle,
    display::Color,
    geometry::{Grid, Insets, Offset, Rect},
    util::include_icon,
};

use super::fonts;
#[cfg(feature = "micropython")]
pub use background::ScreenBackground;
pub use gradient::Gradient;

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
pub const ORANGE_SUPER_DARK: Color = Color::rgb(0x2A, 0x0A, 0x00); // used in gradient

pub const YELLOW: Color = Color::rgb(0xFF, 0xE4, 0x58);
pub const YELLOW_DARK: Color = Color::rgb(0x21, 0x1E, 0x0C); // used in gradient

pub const BLUE: Color = Color::rgb(0x00, 0x46, 0xFF);

pub const RED: Color = Color::rgb(0xFF, 0x30, 0x30);

// Color palette - LED diode
pub const LED_WHITE: Color = Color::rgb(0x23, 0x23, 0x20);
pub const LED_GREEN_LIGHT: Color = Color::rgb(0x04, 0x0D, 0x04);
pub const LED_GREEN_LIME: Color = Color::rgb(0x23, 0x4B, 0x0A);
pub const LED_ORANGE: Color = Color::rgb(0xBC, 0x2A, 0x06);
pub const LED_RED: Color = Color::rgb(0x64, 0x06, 0x03);
pub const LED_YELLOW: Color = Color::rgb(0x16, 0x10, 0x00);
pub const LED_BLUE: Color = Color::rgb(0x05, 0x05, 0x32);

// Common constants
pub const PADDING: i16 = 24; // [px]
pub const HEADER_HEIGHT: i16 = 96; // [px]
pub const SIDE_INSETS: Insets = Insets::sides(PADDING);
pub const ACTION_BAR_HEIGHT: i16 = 90; // [px]
pub const TEXT_VERTICAL_SPACING: i16 = 24; // [px]

// checklist settings
pub const CHECKLIST_CHECK_WIDTH: i16 = 32; // [px]
pub const CHECKLIST_SPACING: i16 = 40; // [px]
pub const CHECKLIST_DONE_OFFSET: Offset = Offset::y(7);
pub const CHECKLIST_CURRENT_OFFSET: Offset = Offset::y(4);

// Tile pattern grid constants
const TILE_SIZE: i16 = ICON_TILE_STRIPES_BACKSLASH.toif.width();
const TILES_ROWS: i16 = 6;
const TILES_COLS: i16 = 4;
// Slightly larger than SCREEN because the bottom row is not full
const TILES_AREA: Rect =
    Rect::from_size(Offset::new(TILES_COLS * TILE_SIZE, TILES_ROWS * TILE_SIZE));
/// Grid for the tiles pattern used in default homescreen and progress screen.
pub const TILES_GRID: Grid = Grid::new(TILES_AREA, TILES_ROWS as usize, TILES_COLS as usize);
/// Indices of the tiles that are slashes ("///") in the default pattern.
pub const TILES_SLASH_INDICES: [usize; 12] = [0, 4, 7, 11, 14, 15, 16, 18, 19, 20, 22, 23];

// UI icons (white color).
include_icon!(ICON_CHEVRON_DOWN, "layout_eckhart/res/chevron_down.toif");
include_icon!(
    ICON_CHEVRON_DOWN_MINI,
    "layout_eckhart/res/chevron_down_mini.toif"
);
include_icon!(
    ICON_CHEVRON_RIGHT_MINI,
    "layout_eckhart/res/chevron_right_mini.toif"
);
include_icon!(
    ICON_CHECKMARK_MINI,
    "layout_eckhart/res/checkmark_mini.toif"
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

// Battery icons
include_icon!(ICON_BATTERY_ZAP, "layout_eckhart/res/battery/zap.toif");
include_icon!(ICON_BATTERY_FULL, "layout_eckhart/res/battery/full.toif");
include_icon!(ICON_BATTERY_MID, "layout_eckhart/res/battery/mid.toif");
include_icon!(ICON_BATTERY_LOW, "layout_eckhart/res/battery/low.toif");
include_icon!(ICON_BATTERY_EMPTY, "layout_eckhart/res/battery/empty.toif");

// Border overlay icons for bootloader screens and hold to confirm animation
include_icon!(ICON_BORDER_BL, "layout_eckhart/res/border/BL_1.toif");
include_icon!(ICON_BORDER_BR, "layout_eckhart/res/border/BR_1.toif");
include_icon!(ICON_BORDER_TOP, "layout_eckhart/res/border/TOP_1.toif");

// Icons for number input screen
include_icon!(ICON_PLUS, "layout_eckhart/res/plus.toif");
include_icon!(ICON_MINUS, "layout_eckhart/res/minus.toif");

// Icon tiles for default pattern
include_icon!(
    ICON_TILE_STRIPES_BACKSLASH, // for "\\\"
    "layout_eckhart/res/defaut_homescreen/hs_tile1.toif"
);
include_icon!(
    ICON_TILE_STRIPES_SLASH, // for "///"
    "layout_eckhart/res/defaut_homescreen/hs_tile2.toif"
);

// Icon for the bootup screen
include_icon!(ICON_SEVEN, "layout_eckhart/res/bootloader/7.toif");

// Tutorial screen icons
include_icon!(ICON_TROPIC, "layout_eckhart/res/tropic.toif");
include_icon!(ICON_SECURED, "layout_eckhart/res/secured.toif");

// Regulatory screen icons
include_icon!(ICON_UKRAINE, "layout_eckhart/res/ukraine.toif");
include_icon!(ICON_KOREA, "layout_eckhart/res/korea_full.toif");
include_icon!(ICON_EUROPE, "layout_eckhart/res/europe.toif");
include_icon!(ICON_RCM, "layout_eckhart/res/rcm.toif");
include_icon!(ICON_FCC, "layout_eckhart/res/fcc.toif");

// Square icon for BLE connection items
include_icon!(ICON_SQUARE, "layout_eckhart/res/square.toif");

// Common text styles and button styles must use fonts accessible from both
// bootloader and firmware

pub const TEXT_NORMAL: TextStyle =
    TextStyle::new(fonts::FONT_SATOSHI_REGULAR_38, GREY_LIGHT, BG, GREY, GREY);
pub const TEXT_SMALL: TextStyle =
    TextStyle::new(fonts::FONT_SATOSHI_MEDIUM_26, GREY_LIGHT, BG, GREY, GREY);
pub const TEXT_SMALL_RED: TextStyle = TextStyle {
    text_color: RED,
    ..TEXT_SMALL
};
pub const TEXT_SMALL_GREY: TextStyle = TextStyle {
    text_color: GREY,
    ..TEXT_SMALL
};
pub const TEXT_SMALL_GREY_EXTRA_LIGHT: TextStyle = TextStyle {
    text_color: GREY_EXTRA_LIGHT,
    ..TEXT_SMALL
};
