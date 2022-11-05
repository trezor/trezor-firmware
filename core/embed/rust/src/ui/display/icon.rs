use crate::{
    trezorhal::display::ToifFormat,
    ui::geometry::{Offset, Point, Rect},
};

use super::{icon_rect, toif_info_ensure, Color};

/// Storing the icon together with its name
/// Needs to be a tuple-struct, so it can be made `const`
#[derive(Debug, Clone, Copy)]
pub struct IconAndName(pub &'static [u8], pub &'static str);

impl IconAndName {
    pub const fn new(icon: &'static [u8], name: &'static str) -> Self {
        Self(icon, name)
    }
}

/// Holding icon data and allowing it to draw itself.
/// Lots of draw methods exist so that we can easily
/// "glue" the icon together with other elements
/// (text, display boundary, etc.) according to their position.
#[derive(Debug, Clone, Copy)]
pub struct Icon {
    pub data: &'static [u8],
    // Text is useful for debugging purposes.
    pub text: &'static str,
    // TODO: could include the info about "real" icon dimensions,
    // accounting for the TOIF limitations (when we sometimes
    // need to have empty row or column) - it could be
    // erasing those empty rows/columns when we draw the icon.
}

// TODO: consider merging it together with ToifInfo
impl Icon {
    pub fn new(icon_and_name: IconAndName) -> Self {
        Icon {
            data: icon_and_name.0,
            text: icon_and_name.1,
        }
    }

    fn toif_info(&self) -> (Offset, &[u8]) {
        toif_info_ensure(self.data, ToifFormat::GrayScaleEH)
    }

    pub fn width(&self) -> i16 {
        self.toif_info().0.x as i16
    }

    pub fn height(&self) -> i16 {
        self.toif_info().0.y as i16
    }

    pub fn toif_size(&self) -> Offset {
        self.toif_info().0
    }

    pub fn toif_data(&self) -> &[u8] {
        self.toif_info().1
    }

    /// Display icon at a specified Rectangle.
    fn draw_icon_rect(&self, r: Rect, fg_color: Color, bg_color: Color) {
        icon_rect(r, self.toif_data(), fg_color, bg_color);
    }

    /// Display the icon with left top baseline Point.
    pub fn draw_top_left(&self, baseline: Point, fg_color: Color, bg_color: Color) {
        let r = Rect::from_top_left_and_size(baseline, self.toif_size());
        self.draw_icon_rect(r, fg_color, bg_color);
    }

    /// Display the icon with right top baseline Point.
    pub fn draw_top_right(&self, baseline: Point, fg_color: Color, bg_color: Color) {
        let r = Rect::from_top_right_and_size(baseline, self.toif_size());
        self.draw_icon_rect(r, fg_color, bg_color);
    }

    /// Display the icon with right bottom baseline Point.
    pub fn draw_bottom_right(&self, baseline: Point, fg_color: Color, bg_color: Color) {
        let r = Rect::from_bottom_right_and_size(baseline, self.toif_size());
        self.draw_icon_rect(r, fg_color, bg_color);
    }

    /// Display the icon with left bottom baseline Point.
    pub fn draw_bottom_left(&self, baseline: Point, fg_color: Color, bg_color: Color) {
        let r = Rect::from_bottom_left_and_size(baseline, self.toif_size());
        self.draw_icon_rect(r, fg_color, bg_color);
    }

    /// Display the icon around center Point.
    pub fn draw_center(&self, center: Point, fg_color: Color, bg_color: Color) {
        let r = Rect::from_center_and_size(center, self.toif_size());
        self.draw_icon_rect(r, fg_color, bg_color);
    }
}
