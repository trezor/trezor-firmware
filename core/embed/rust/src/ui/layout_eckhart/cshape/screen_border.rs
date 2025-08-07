use crate::ui::{
    display::Color,
    geometry::{Alignment2D, Insets, Rect},
    shape::{self, Renderer},
};

use super::super::{
    constant::SCREEN,
    theme::{ICON_BORDER_BL, ICON_BORDER_BR, ICON_BORDER_TOP},
};

/// Custom shape for a full screen border overlay, parameterizable by color. In
/// order to look same-width along the whole screen, the border is placed 1px
/// from the actual border to account for minor variations in display
/// production.
pub struct ScreenBorder {
    color: Color,
    side_bars: [Rect; 3],
}

impl ScreenBorder {
    pub const TOTAL_WIDTH: i16 = 5;
    pub const LINE_WIDTH: i16 = Self::TOTAL_WIDTH - 1;
    pub const TOP_ARC_HEIGHT: i16 = ICON_BORDER_TOP.toif.height();
    pub const SCREEN_SHRUNK: Rect = SCREEN.inset(Insets::uniform(1));

    pub const fn new(color: Color) -> Self {
        // Bottom bar: from the right edge of bottom-left icon to the left edge of
        // bottom-right icon.
        let bottom_bar_rect = Rect {
            x0: Self::SCREEN_SHRUNK.x0 + ICON_BORDER_BL.toif.width(),
            y0: Self::SCREEN_SHRUNK.y1 - Self::LINE_WIDTH,
            x1: Self::SCREEN_SHRUNK.x1 - ICON_BORDER_BR.toif.width(),
            y1: Self::SCREEN_SHRUNK.y1,
        };

        // Left bar: from the bottom edge of top-left icon to the top edge of
        // bottom-left icon.
        let left_bar_rect = Rect {
            x0: Self::SCREEN_SHRUNK.x0,
            y0: Self::SCREEN_SHRUNK.y0 + Self::TOP_ARC_HEIGHT,
            x1: Self::SCREEN_SHRUNK.x0 + Self::LINE_WIDTH,
            y1: Self::SCREEN_SHRUNK.y1 - ICON_BORDER_BL.toif.height(),
        };

        // Right bar: from the bottom edge of top-right icon to the top edge of
        // bottom-right icon.
        let right_bar_rect = Rect {
            x0: Self::SCREEN_SHRUNK.x1 - Self::LINE_WIDTH,
            y0: Self::SCREEN_SHRUNK.y0 + Self::TOP_ARC_HEIGHT,
            x1: Self::SCREEN_SHRUNK.x1,
            y1: Self::SCREEN_SHRUNK.y1 - ICON_BORDER_BR.toif.height(),
        };
        Self {
            color,
            side_bars: [bottom_bar_rect, left_bar_rect, right_bar_rect],
        }
    }

    pub fn render<'s>(&'s self, alpha: u8, target: &mut impl Renderer<'s>) {
        self.side_bars.iter().for_each(|bar| {
            shape::Bar::new(*bar)
                .with_bg(self.color)
                .with_alpha(alpha)
                .render(target);
        });

        // Draw the irregular corner shapes
        [
            (
                Self::SCREEN_SHRUNK.top_left(),
                ICON_BORDER_TOP.toif,
                Alignment2D::TOP_LEFT,
            ),
            (
                Self::SCREEN_SHRUNK.bottom_left(),
                ICON_BORDER_BL.toif,
                Alignment2D::BOTTOM_LEFT,
            ),
            (
                Self::SCREEN_SHRUNK.bottom_right(),
                ICON_BORDER_BR.toif,
                Alignment2D::BOTTOM_RIGHT,
            ),
        ]
        .iter()
        .for_each(|(position, toif, alignment)| {
            shape::ToifImage::new(*position, *toif)
                .with_align(*alignment)
                .with_fg(self.color)
                .with_alpha(alpha)
                .render(target);
        });
    }
}
