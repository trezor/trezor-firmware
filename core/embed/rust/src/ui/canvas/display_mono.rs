use crate::ui::{display::Color, geometry::Offset};

use super::{BasicCanvas, Canvas, Mono8Canvas};

use crate::trezorhal::display;

pub struct MonoDisplay<'a> {
    canvas: Mono8Canvas<'a>,
}

impl<'a> MonoDisplay<'a> {
    pub fn new(size: Offset, buff: &'a mut [u8]) -> Option<Self> {
        Some(Self {
            canvas: Mono8Canvas::new(size, None, buff)?,
        })
    }

    pub fn canvas(&mut self) -> &mut Mono8Canvas<'a> {
        &mut self.canvas
    }

    pub fn refresh(&self) {
        // TODO:

        let w = self.canvas.width() as u16 - 1;
        let h = self.canvas.height() as u16 - 1;
        display::set_window(0, 0, w, h);

        let view = self.canvas.view();

        for y in 0..self.canvas.size().y {
            let row = unwrap!(view.row(y));
            for value in row.iter() {
                let c = Color::rgb(*value, *value, *value);
                display::pixeldata(c.into());
            }
        }

        display::refresh();
    }
}
