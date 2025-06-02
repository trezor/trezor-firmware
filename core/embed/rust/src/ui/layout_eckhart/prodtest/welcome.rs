use super::super::{cshape::ScreenBorder, fonts, theme::WHITE};
use crate::{
    strutil::format_i64,
    trezorhal::power_manager::{charging_state, soc, ChargingState},
    ui::{
        component::{Component, Event, EventCtx, Never, Qr},
        constant::screen,
        display::Color,
        geometry::{Alignment, Offset, Point, Rect},
        shape::{self, Renderer},
    },
};

pub struct Welcome {
    id: Option<&'static str>,
    id_text_pos: Option<Point>,
    qr: Option<Qr>,
    screen_border: ScreenBorder,
}

impl Welcome {
    pub fn new(id: Option<&'static str>) -> Self {
        let qr = if let Some(id) = id {
            let qr = Qr::new(id, true);
            let qr = unwrap!(qr).with_border(4);
            Some(qr)
        } else {
            None
        };

        Self {
            id,
            id_text_pos: None,
            qr,
            screen_border: ScreenBorder::new(Color::white()),
        }
    }
}

impl Component for Welcome {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        if self.id.is_some() {
            // place the qr in the middle of the screen and size it to half the screen
            let qr_width = screen().width() / 2;

            let qr_area = Rect::from_top_center_and_size(
                screen().top_center() + Offset::y(5),
                Offset::uniform(qr_width),
            );
            self.qr.place(qr_area);

            self.id_text_pos = Some(qr_area.bottom_center() + Offset::y(10));
        }
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        if let Event::PM(e) = _event {
            if e.soc_updated {
                ctx.request_paint();
            }
            if e.charging_status_changed {
                ctx.request_paint();
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.screen_border.render(u8::MAX, target);

        let mut buf = [0; 20];
        let text = unwrap!(format_i64(soc() as _, &mut buf));

        shape::Text::new(screen().center(), text, fonts::FONT_SATOSHI_REGULAR_22)
            .with_fg(WHITE)
            .with_align(Alignment::Center)
            .render(target);

        let state = charging_state();

        let text = match state {
            ChargingState::Charging => "Charging",
            ChargingState::Discharging => "Discharging",
            ChargingState::Idle => "Idle",
        };

        shape::Text::new(
            screen().center() + Offset::y(20),
            text,
            fonts::FONT_SATOSHI_REGULAR_22,
        )
        .with_align(Alignment::Center)
        .render(target);

        self.qr.render(target);

        if let Some(pos) = self.id_text_pos {
            shape::Text::new(pos, unwrap!(self.id), fonts::FONT_SATOSHI_REGULAR_22)
                .with_fg(WHITE)
                .with_align(Alignment::Center)
                .render(target);
        }
    }
}
