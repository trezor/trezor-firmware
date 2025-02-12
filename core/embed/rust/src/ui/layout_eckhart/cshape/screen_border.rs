use crate::ui::{
    display::Color,
    geometry::{Alignment2D, Rect},
    shape::{self, Renderer},
};

use super::super::{
    constant,
    theme::{ICON_BORDER_BL, ICON_BORDER_BR, ICON_BORDER_TL, ICON_BORDER_TR},
};

/// Custom shape for a full screen border overlay, parameterizable by color.
pub struct ScreenBorder {
    color: Color,
    side_bars: [Rect; 4],
}

impl ScreenBorder {
    pub fn new(color: Color) -> Self {
        let screen = constant::screen();

        // Top bar: from the right edge of top-left icon to the left edge of top-right icon.
        let top_bar_rect = Rect {
            x0: screen.x0 + ICON_BORDER_TL.toif.width(),
            y0: screen.y0,
            x1: screen.x1 - ICON_BORDER_TR.toif.width(),
            y1: screen.y0 + 2,
        };

        // Bottom bar: from the right edge of bottom-left icon to the left edge of bottom-right icon.
        let bottom_bar_rect = Rect {
            x0: screen.x0 + ICON_BORDER_BL.toif.width(),
            y0: screen.y1 - 2,
            x1: screen.x1 - ICON_BORDER_BR.toif.width(),
            y1: screen.y1,
        };

        // Left bar: from the bottom edge of top-left icon to the top edge of bottom-left icon.
        let left_bar_rect = Rect {
            x0: screen.x0,
            y0: screen.y0 + ICON_BORDER_TL.toif.height() - 1,
            x1: screen.x0 + 2,
            y1: screen.y1 - ICON_BORDER_BL.toif.height(),
        };
        // Right bar: from the bottom edge of top-right icon to the top edge of bottom-right icon.
        let right_bar_rect = Rect {
            x0: screen.x1 - 2,
            y0: screen.y0 + ICON_BORDER_TR.toif.height() - 1,
            x1: screen.x1,
            y1: screen.y1 - ICON_BORDER_BR.toif.height(),
        };
        Self {
            color,
            side_bars: [bottom_bar_rect, left_bar_rect, right_bar_rect, top_bar_rect],
        }
    }

    pub fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let screen = constant::screen();

        // Draw the four side bars.
        for bar in self.side_bars {
            shape::Bar::new(bar)
                .with_fg(self.color)
                .with_thickness(2)
                .render(target);
        }
        // Draw the four corners.
        shape::ToifImage::new(screen.bottom_left(), ICON_BORDER_BL.toif)
            .with_fg(self.color)
            .with_align(Alignment2D::BOTTOM_LEFT)
            .render(target);
        shape::ToifImage::new(screen.top_right(), ICON_BORDER_TR.toif)
            .with_fg(self.color)
            .with_align(Alignment2D::TOP_RIGHT)
            .render(target);
        shape::ToifImage::new(screen.top_left(), ICON_BORDER_TL.toif)
            .with_fg(self.color)
            .with_align(Alignment2D::TOP_LEFT)
            .render(target);
        shape::ToifImage::new(screen.bottom_right(), ICON_BORDER_BR.toif)
            .with_fg(self.color)
            .with_align(Alignment2D::BOTTOM_RIGHT)
            .render(target);
    }
}
