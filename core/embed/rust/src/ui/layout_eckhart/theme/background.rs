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
    /// Step size for the gradient (1 = full quality, higher = faster but lower
    /// quality)
    step_size: u16,
}

impl ScreenBackground {
    pub fn new(step_size: Option<u16>) -> Self {
        Self {
            step_size: step_size.unwrap_or(1),
        }
    }

    /// Renders the homescreen background
    ///
    /// # Arguments
    /// * `target` - The renderer to draw to
    /// * `led_simulation` - Optional LED color for the LED simulation layer
    pub fn render<'s>(&self, target: &mut impl Renderer<'s>, led_simulation: Option<(Color, u8)>) {
        // Layer 1: Base Solid Colour
        shape::Bar::new(SCREEN)
            .with_bg(theme::GREY_EXTRA_DARK)
            .render(target);

        // Layer 2: Base Gradient overlay
        Gradient::HomescreenBase.render(target, SCREEN, self.step_size);

        if let Some((led_color, led_alpha)) = led_simulation {
            // Layer 3: (Optional) LED lightning simulation
            let gradient_area = SCREEN.inset(Insets::bottom(theme::ACTION_BAR_HEIGHT));
            Gradient::ScreenLEDSim(led_color, led_alpha).render(
                target,
                gradient_area,
                self.step_size,
            );
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
