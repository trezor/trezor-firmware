use super::super::{
    fonts,
    theme::{bootloader::WELCOME_COLOR, WHITE},
};
use crate::ui::{
    component::{Component, Event, EventCtx, Never, Pad, Qr},
    constant::screen,
    geometry::{Alignment, Offset, Point, Rect},
    shape::{self, Renderer},
};
#[cfg(feature = "power_manager")]
use crate::{
    strutil::format_i64,
    trezorhal::power_manager::{charging_state, soc, ChargingState},
};

pub struct Welcome {
    bg: Pad,
    id: Option<&'static str>,
    id_text_pos: Option<Point>,
    qr: Option<Qr>,
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
            bg: Pad::with_background(WELCOME_COLOR).with_clear(),
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
            let qr_width = screen().width() / 2;

            let qr_area = Rect::from_top_center_and_size(
                screen().top_center() + Offset::y(5),
                Offset::uniform(qr_width),
            );
            self.qr.place(qr_area);

            self.id_text_pos = Some(qr_area.bottom_center() + Offset::y(10));
        }
        self.bg.place(screen());
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        #[cfg(feature = "power_manager")]
        if let Event::PM(e) = _event {
            if e.soc_updated {
                _ctx.request_paint();
            }
            if e.charging_status_changed {
                _ctx.request_paint();
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);
        shape::Bar::new(screen())
            .with_fg(crate::ui::display::color::Color::white())
            .with_thickness(1)
            .render(target);

        #[cfg(feature = "power_manager")]
        {
            let mut buf = [0; 20];
            let text = unwrap!(format_i64(soc() as _, &mut buf));

            shape::Text::new(screen().center(), text, fonts::FONT_BOLD_UPPER)
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
                fonts::FONT_BOLD_UPPER,
            )
            .with_align(Alignment::Center)
            .render(target);
        }
        self.qr.render(target);

        if let Some(pos) = self.id_text_pos {
            shape::Text::new(pos, unwrap!(self.id), fonts::FONT_BOLD_UPPER)
                .with_fg(WHITE)
                .with_align(Alignment::Center)
                .render(target);
        }
    }
}
