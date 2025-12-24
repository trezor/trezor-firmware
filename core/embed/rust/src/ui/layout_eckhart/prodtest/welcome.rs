use super::super::{
    component::{Button, ButtonMsg},
    constant::SCREEN,
    cshape::ScreenBorder,
    fonts,
    theme::{bootloader::button_cancel, BLUE, GREEN, RED, WHITE},
};
use crate::{
    strutil::format_i64,
    trezorhal::power_manager::{
        charging_disable, charging_enable, charging_state, is_charging_limited, is_ntc_connected,
        soc, ChargingState,
    },
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
    // Error state triggered by NTC connected change entering true
    error_active: bool,
    // Headline of the error, based on the triggering condition
    error_headline: &'static str,
    // Prepared Button component to exit error state
    exit_btn: Button,
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

        // Determine initial error state and headline
        let (error_active, error_headline) = if !is_ntc_connected() {
            (true, "NTC Error")
        } else if is_charging_limited() {
            (true, "Charging Limited")
        } else {
            (false, "Error")
        };

        Self {
            id,
            id_text_pos: None,
            qr,
            screen_border: ScreenBorder::new(Color::white()),
            // Enter error state based on startup conditions
            error_active,
            error_headline,
            // Use prepared Button component
            exit_btn: Button::with_text("Exit".into()).styled(button_cancel()),
        }
    }
}

impl Component for Welcome {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        // Compute button rect for error state and place the prepared Button component
        let btn_width = screen().width() * 3 / 5; // 60% width
        let btn_height = 84; // px
        let btn_area = Rect::from_center_and_size(
            screen().bottom_center() - Offset::y(80),
            Offset::new(btn_width, btn_height),
        );
        self.exit_btn.place(btn_area);

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
        match _event {
            Event::Attach(_) => {
                if self.error_active {
                    ctx.request_paint();
                }
                None
            }
            Event::PM(e) => {
                if e.soc_updated || e.charging_status_changed {
                    ctx.request_paint();
                }
                // Error case: NTC connected changed and is now false
                if e.ntc_connected_changed && !is_ntc_connected() {
                    self.error_active = true;
                    self.error_headline = "NTC Error";
                    charging_disable();
                    ctx.request_paint();
                }
                // Error case: charging limited changed and is now true
                if e.charging_limited_changed && is_charging_limited() {
                    self.error_active = true;
                    self.error_headline = "Charging Limited";
                    charging_disable();
                    ctx.request_paint();
                }
                // Error case: Battery temperature jump detected event
                if e.battery_temp_jump_detected {
                    self.error_active = true;
                    self.error_headline = "Battery Temp Jump";
                    charging_disable();
                    ctx.request_paint();
                }
                // Error case: Battery OCV jump detected event
                if e.battery_ocv_jump_detected {
                    self.error_active = true;
                    charging_disable();
                    self.error_headline = "Battery OCV Jump";
                    ctx.request_paint();
                }
                None
            }
            Event::Touch(t) => {
                // In error mode, delegate touch events to the prepared Button
                if self.error_active {
                    if let Some(ButtonMsg::Clicked) = self.exit_btn.event(ctx, Event::Touch(t)) {
                        self.error_active = false;
                        charging_enable();
                        ctx.request_paint();
                    }
                }
                None
            }
            _ => None,
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if self.error_active {
            // Error screen rendering
            shape::Bar::new(SCREEN).with_bg(RED).render(target);
            self.screen_border.render(u8::MAX, target);

            // Error message
            shape::Text::new(
                screen().center() - Offset::y(20),
                self.error_headline,
                fonts::FONT_SATOSHI_REGULAR_38,
            )
            .with_fg(WHITE)
            .with_align(Alignment::Center)
            .render(target);

            shape::Text::new(
                screen().center() + Offset::y(12),
                "Tap to exit error",
                fonts::FONT_SATOSHI_REGULAR_22,
            )
            .with_fg(WHITE)
            .with_align(Alignment::Center)
            .render(target);

            // Render the prepared Button component
            self.exit_btn.render(target);
            return;
        }

        let state = charging_state();

        let (state_text, bg_color) = match state {
            ChargingState::Charging => ("Charging", Color::black()),
            ChargingState::Discharging => ("Discharging", BLUE),
            ChargingState::Idle => ("Idle", GREEN),
        };

        shape::Bar::new(SCREEN).with_bg(bg_color).render(target);

        self.screen_border.render(u8::MAX, target);

        let mut buf = [0; 20];
        let text = unwrap!(format_i64(soc() as _, &mut buf));

        shape::Text::new(
            screen().center(),
            state_text,
            fonts::FONT_SATOSHI_REGULAR_22,
        )
        .with_fg(WHITE)
        .with_align(Alignment::Center)
        .render(target);

        shape::Text::new(
            screen().center() + Offset::y(40),
            text,
            fonts::FONT_SATOSHI_REGULAR_38,
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
