use crate::ui::{
    display::Color,
    geometry::{Alignment2D, Insets},
    shape::{self, Renderer},
};

use super::super::{
    constant::SCREEN,
    theme::{self, Gradient, TILES_GRID},
};

#[derive(Clone, Copy, PartialEq, Eq)]
pub struct ScreenBackground {
    /// LED color for the simulation
    led_color: Option<Color>,
    /// Step size for the gradient (1 = full quality, higher = faster but lower
    /// quality)
    step_size: u16,
}

impl ScreenBackground {
    pub fn new(led_color: Option<Color>, step_size: Option<u16>) -> Self {
        Self {
            led_color,
            step_size: step_size.unwrap_or(1),
        }
    }

    /// Renders the homescreen background
    ///
    /// # Arguments
    /// * `target` - The renderer to draw to
    pub fn render<'s>(&self, target: &mut impl Renderer<'s>) {
        // Layer 1: Base Solid Colour
        shape::Bar::new(SCREEN)
            .with_bg(theme::GREY_EXTRA_DARK)
            .render(target);

        // Layer 2: Base Gradient overlay
        Gradient::HomescreenBase.render(target, SCREEN, self.step_size);

        if let Some(led_color) = self.led_color {
            // Layer 3: (Optional) LED lightning simulation
            let gradient_area = SCREEN.inset(Insets::bottom(theme::ACTION_BAR_HEIGHT));
            Gradient::ScreenLEDSim(led_color).render(target, gradient_area, self.step_size);
        }

        // Layer 4: Tile pattern
        // TODO: improve frame rate
        for idx in 0..TILES_GRID.cell_count() {
            let tile_area = TILES_GRID.cell(idx);
            let icon = if theme::TILES_SLASH_INDICES.contains(&idx) {
                theme::ICON_TILE_STRIPES_SLASH.toif
            } else {
                theme::ICON_TILE_STRIPES_BACKSLASH.toif
            };
            shape::ToifImage::new(tile_area.top_left(), icon)
                .with_align(Alignment2D::TOP_LEFT)
                .with_fg(theme::BLACK)
                .render(target);
        }
    }
}
