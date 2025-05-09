use super::super::theme::{BLACK, WHITE};
use crate::ui::{
    component::{Component, Event, EventCtx, Never, Qr},
    constant::screen,
    geometry::{Offset, Point, Rect},
    shape::{self, Renderer},
};

pub struct Welcome {
    id: Option<&'static str>,
    id_text_pos: Option<Point>,
    qr: Option<Qr>,
}

impl Welcome {
    pub fn new(id: Option<&'static str>) -> Self {
        let qr = if let Some(id) = id {
            let qr = Qr::new(id, true);
            let qr = unwrap!(qr).with_border(1);
            Some(qr)
        } else {
            None
        };

        Self {
            id,
            id_text_pos: None,
            qr,
        }
    }
}

impl Component for Welcome {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        if self.id.is_some() {
            // place the qr in the middle of the screen and size it to half the screen
            let qr_width = 50;

            let qr_area = Rect::from_center_and_size(screen().center(), Offset::uniform(qr_width))
                .translate(Offset::y(-5));
            self.qr.place(qr_area);

            self.id_text_pos = Some(qr_area.bottom_center() + Offset::y(10));
        }
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let bg_color = if self.id.is_some() { BLACK } else { WHITE };

        shape::Bar::new(screen())
            .with_fg(WHITE)
            .with_bg(bg_color)
            .with_thickness(1)
            .render(target);

        self.qr.render(target);
    }
}
