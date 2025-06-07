use crate::{
    trezorhal::power_manager::{self, ChargingState},
    ui::{
        component::{Component, Event, EventCtx, Never, Timer},
        display::Font,
        geometry::{Alignment, Alignment2D, Offset, Point, Rect},
        shape::{self, Renderer},
        util::animation_disabled,
    },
};

use super::super::{fonts, theme};

/// Component for showing a small fuel gauge (battery status) consisting of:
/// - icon indicating charging or discharging state
/// - percentage
#[derive(Clone)]
pub struct FuelGauge {
    /// Area where the fuel gauge is rendered
    area: Rect,
    /// Alignment of the fuel gauge within its area
    alignment: Alignment,
    /// Mode of the fuel gauge (Always or OnChrgStatusChange)
    mode: FuelGaugeMode,
    /// State of battery charging
    charging_state: ChargingState,
    /// State of charge (0-100) [%]
    soc: Option<u8>,
    /// Timer to track temporary battery status showcase
    timer: Timer,
    /// Whether the fuel gauge is currently showing
    showing_temporarily: bool,
    /// Font used for the soc percentage
    font: Font,
}

#[derive(Clone, PartialEq)]
pub enum FuelGaugeMode {
    /// Always show the fuel gauge
    Always,
    /// Show the fuel gauge only when charging state changes
    OnChrgChange,
    /// Show the fuel gauge when charging state changes or when attached
    OnChrgChangeAndAttach,
}

impl FuelGauge {
    pub const fn new_always() -> Self {
        Self::new(FuelGaugeMode::Always)
    }

    pub const fn new_on_chrg_status_change() -> Self {
        Self::new(FuelGaugeMode::OnChrgChange)
    }

    pub const fn new_on_chrg_status_change_and_attach() -> Self {
        Self::new(FuelGaugeMode::OnChrgChangeAndAttach)
    }

    pub const fn with_alignment(mut self, alignment: Alignment) -> Self {
        self.alignment = alignment;
        self
    }

    pub const fn with_font(mut self, font: Font) -> Self {
        self.font = font;
        self
    }

    pub fn update_pm_state(&mut self) {
        self.soc = Some(power_manager::soc());
        self.charging_state = power_manager::charging_state();
    }

    pub fn should_be_shown(&self) -> bool {
        match self.mode {
            FuelGaugeMode::Always => true,
            FuelGaugeMode::OnChrgChange | FuelGaugeMode::OnChrgChangeAndAttach => {
                self.showing_temporarily
            }
        }
    }

    const fn new(mode: FuelGaugeMode) -> Self {
        Self {
            area: Rect::zero(),
            alignment: Alignment::Start,
            mode,
            charging_state: ChargingState::Idle,
            soc: None,
            timer: Timer::new(),
            showing_temporarily: false,
            font: fonts::FONT_SATOSHI_REGULAR_22,
        }
    }
}

impl Component for FuelGauge {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Attach(_) = event {
            if self.soc.is_none() {
                self.update_pm_state();
            }
            self.update_pm_state();
            if !animation_disabled() && self.mode == FuelGaugeMode::OnChrgChangeAndAttach {
                self.showing_temporarily = true;
                self.timer.start(ctx, theme::firmware::FUEL_GAUGE_DURATION);
            }
            ctx.request_paint();
        }

        if let Event::PM(e) = event {
            self.update_pm_state();
            match self.mode {
                FuelGaugeMode::Always => {
                    ctx.request_paint();
                }
                FuelGaugeMode::OnChrgChange | FuelGaugeMode::OnChrgChangeAndAttach => {
                    if e.charging_status_changed {
                        self.showing_temporarily = true;
                        self.timer.start(ctx, theme::firmware::FUEL_GAUGE_DURATION);
                        ctx.request_paint();
                    }
                }
            }
        }

        if let Event::Timer(_) = event {
            if self.timer.expire(event) {
                self.showing_temporarily = false;
                ctx.request_paint();
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        const ICON_PERCENT_GAP: i16 = 16;

        let soc = self.soc.unwrap_or(u8::MAX);
        let (icon, color_icon, color_text) = match self.charging_state {
            ChargingState::Charging => (theme::ICON_BATTERY_ZAP, theme::YELLOW, theme::GREY_LIGHT),
            ChargingState::Discharging | ChargingState::Idle => {
                if soc > 80 {
                    (
                        theme::ICON_BATTERY_FULL,
                        theme::GREY_LIGHT,
                        theme::GREY_LIGHT,
                    )
                } else if soc > 25 {
                    (
                        theme::ICON_BATTERY_MID,
                        theme::GREY_LIGHT,
                        theme::GREY_LIGHT,
                    )
                } else if soc > 9 {
                    (theme::ICON_BATTERY_LOW, theme::YELLOW, theme::GREY_LIGHT)
                } else {
                    (theme::ICON_BATTERY_EMPTY, theme::RED, theme::RED)
                }
            }
        };
        let soc_percent_fmt = if self.soc.is_none() {
            uformat!("--")
        } else {
            uformat!("{}%", soc)
        };
        let text_width = self.font.text_width(&soc_percent_fmt);
        let text_height = self.font.text_height();
        let icon_width = icon.toif.width();
        let icon_height = icon.toif.height();

        let (point, alignment) = match self.alignment {
            Alignment::Start => (self.area.left_center(), Alignment2D::CENTER_LEFT),
            Alignment::End => (self.area.right_center(), Alignment2D::CENTER_RIGHT),
            Alignment::Center => (self.area.center(), Alignment2D::CENTER),
        };

        let area = Rect::snap(
            point,
            Offset::new(
                icon_width + ICON_PERCENT_GAP + text_width,
                text_height.max(icon_height),
            ),
            alignment,
        );
        let text_y_coord = self.font.vert_center(area.y0, area.y1, &soc_percent_fmt);

        shape::ToifImage::new(area.left_center(), icon.toif)
            .with_fg(color_icon)
            .with_align(Alignment2D::CENTER_LEFT)
            .render(target);

        shape::Text::new(
            Point::new(area.x1, text_y_coord),
            &soc_percent_fmt,
            self.font,
        )
        .with_fg(color_text)
        .with_align(Alignment::End)
        .render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for FuelGauge {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("FuelGauge");
        t.int("soc", self.soc.unwrap_or(u8::MAX) as i64);
    }
}
