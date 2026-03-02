use crate::{
    strutil::ShortString,
    trezorhal::power_manager::{self, ChargingState},
    ui::{
        component::{Component, Event, EventCtx, Never},
        display::{Color, Font, Icon},
        geometry::{Alignment, Alignment2D, Offset, Point, Rect},
        shape::{self, Renderer},
    },
};

#[cfg(feature = "micropython")]
use crate::ui::component::Timer;

use super::super::{
    fonts,
    theme::{
        GREY_LIGHT, ICON_BATTERY_EMPTY, ICON_BATTERY_FULL, ICON_BATTERY_LOW,
        ICON_BATTERY_MID_MINUS, ICON_BATTERY_MID_PLUS, ICON_BATTERY_ZAP, RED, YELLOW,
    },
};

#[cfg(feature = "micropython")]
use super::super::theme::firmware::FUEL_GAUGE_DURATION;

const ICON_PERCENT_GAP: i16 = 16;

/// Component for showing a small fuel gauge (battery status) consisting of:
/// - icon indicating charging or discharging state
/// - percentage
#[derive(Clone)]
pub struct FuelGauge {
    /// Area where the fuel gauge is rendered
    pub area: Rect,
    /// Mode of the fuel gauge (Always or OnChrgStatusChange)
    mode: FuelGaugeMode,
    /// State of battery charging
    charging_state: ChargingState,
    /// State of charge (0-100) [%]
    soc: Option<u8>,
    /// Cached formatted SOC text
    soc_text: ShortString,
    /// Font used for the soc percentage
    font: Font,
    /// Cached indication (icon, icon color, text color) based on the last known
    /// charging state and soc.
    battery_indication: (Icon, Color, Color),
}

#[derive(Clone)]
pub enum FuelGaugeMode {
    /// Always show the fuel gauge, both icon and percentage
    AlwaysFull,
    /// Always show the fuel gauge, but only icon
    AlwaysIconOnly,
    /// Show only charging icon when the device is charging
    ChargingIconOnly,
    /// Show the fuel gauge only when charging state changes
    #[cfg(feature = "micropython")]
    OnChargingChange(Timer),
}

impl FuelGauge {
    pub const fn always() -> Self {
        Self::new(FuelGaugeMode::AlwaysFull)
    }

    pub const fn always_icon_only() -> Self {
        Self::new(FuelGaugeMode::AlwaysIconOnly)
    }

    pub const fn charging_icon_only() -> Self {
        Self::new(FuelGaugeMode::ChargingIconOnly)
    }

    #[cfg(feature = "micropython")]
    pub const fn on_charging_change() -> Self {
        Self::new(FuelGaugeMode::OnChargingChange(Timer::new()))
    }

    pub fn update_pm_state(&mut self) {
        self.soc = Some(power_manager::soc());
        self.charging_state = power_manager::charging_state();
        self.soc_text = uformat!("{} %", self.soc.unwrap_or(0));
        self.battery_indication =
            self.battery_indication(self.charging_state, self.soc.unwrap_or(0));
    }

    pub fn should_be_shown(&self) -> bool {
        match &self.mode {
            FuelGaugeMode::AlwaysFull | FuelGaugeMode::AlwaysIconOnly => true,
            FuelGaugeMode::ChargingIconOnly => {
                matches!(self.charging_state, ChargingState::Charging)
            }
            #[cfg(feature = "micropython")]
            FuelGaugeMode::OnChargingChange(timer) => timer.is_running(),
        }
    }

    /// Returns the total rendered width of the fuel gauge content.
    pub fn content_width(&self) -> i16 {
        let icon_width = self.battery_indication.0.toif.width();
        match self.mode {
            FuelGaugeMode::AlwaysIconOnly | FuelGaugeMode::ChargingIconOnly => icon_width,
            _ => icon_width + ICON_PERCENT_GAP + self.font.text_width(&self.soc_text),
        }
    }

    fn render_icon<'s>(&self, area: Rect, target: &mut impl Renderer<'s>) {
        shape::ToifImage::new(area.left_center(), self.battery_indication.0.toif)
            .with_fg(self.battery_indication.1)
            .with_align(Alignment2D::CENTER_LEFT)
            .render(target);
    }

    const fn new(mode: FuelGaugeMode) -> Self {
        #[cfg(feature = "micropython")]
        let font = fonts::FONT_SATOSHI_REGULAR_22;
        #[cfg(not(feature = "micropython"))]
        let font = fonts::FONT_SATOSHI_MEDIUM_26;
        Self {
            area: Rect::zero(),
            mode,
            charging_state: ChargingState::Idle,
            soc: None,
            soc_text: ShortString::new(),
            font,
            battery_indication: (ICON_BATTERY_EMPTY, GREY_LIGHT, GREY_LIGHT),
        }
    }

    /// Returns the icon, color for the icon, and color for the text based on
    /// the charging state and state of charge (soc).
    fn battery_indication(&self, charging_state: ChargingState, soc: u8) -> (Icon, Color, Color) {
        const SOC_THRESHOLD_FULL: u8 = 90;
        const SOC_THRESHOLD_MID_PLUS: u8 = 40;
        const SOC_THRESHOLD_MID_MINUS: u8 = 20;
        const SOC_THRESHOLD_LOW: u8 = 10;
        match charging_state {
            ChargingState::Charging => (ICON_BATTERY_ZAP, YELLOW, GREY_LIGHT),
            ChargingState::Discharging | ChargingState::Idle => {
                let icon = match soc {
                    x if x >= SOC_THRESHOLD_FULL => ICON_BATTERY_FULL,
                    x if x >= SOC_THRESHOLD_MID_PLUS => ICON_BATTERY_MID_PLUS,
                    x if x >= SOC_THRESHOLD_MID_MINUS => ICON_BATTERY_MID_MINUS,
                    x if x >= SOC_THRESHOLD_LOW => ICON_BATTERY_LOW,
                    _ => ICON_BATTERY_EMPTY,
                };
                let (icon_color, text_color) = match soc {
                    x if x >= SOC_THRESHOLD_MID_MINUS => (GREY_LIGHT, GREY_LIGHT),
                    x if x >= SOC_THRESHOLD_LOW => (YELLOW, GREY_LIGHT),
                    _ => (RED, RED),
                };
                (icon, icon_color, text_color)
            }
        }
    }

    fn render_icon_and_percentage<'s>(&self, area: Rect, target: &mut impl Renderer<'s>) {
        self.render_icon(area, target);
        let text_y_coord = self.font.vert_center(area.y0, area.y1, &self.soc_text);
        shape::Text::new(Point::new(area.x1, text_y_coord), &self.soc_text, self.font)
            .with_fg(self.battery_indication.2)
            .with_align(Alignment::End)
            .render(target);
    }
}

impl Component for FuelGauge {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            Event::Attach(_) => {
                if self.soc.is_none() {
                    self.update_pm_state();
                }
                ctx.request_paint();
            }
            Event::PM(_e) => {
                self.update_pm_state();
                match &mut self.mode {
                    FuelGaugeMode::AlwaysFull | FuelGaugeMode::AlwaysIconOnly => {
                        ctx.request_paint();
                    }
                    FuelGaugeMode::ChargingIconOnly => {
                        if _e.charging_status_changed {
                            ctx.request_paint();
                        }
                    }
                    #[cfg(feature = "micropython")]
                    FuelGaugeMode::OnChargingChange(timer) => {
                        if _e.charging_status_changed {
                            timer.start(ctx, FUEL_GAUGE_DURATION.into());
                            ctx.request_paint();
                        }
                    }
                }
            }
            #[cfg(feature = "micropython")]
            Event::Timer(_) => {
                if let FuelGaugeMode::OnChargingChange(timer) = &mut self.mode {
                    if timer.expire(event) {
                        ctx.request_paint();
                    }
                }
            }
            _ => {}
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let text_width = self.font.text_width(&self.soc_text);
        let text_height = self.font.text_height();
        let icon = self.battery_indication.0.toif;
        let icon_width = icon.width();
        let icon_height = icon.height();

        let (point, alignment) = (self.area.left_center(), Alignment2D::CENTER_LEFT);
        let area = Rect::snap(
            point,
            Offset::new(
                icon_width + ICON_PERCENT_GAP + text_width,
                text_height.max(icon_height),
            ),
            alignment,
        );

        match self.mode {
            FuelGaugeMode::AlwaysIconOnly => {
                self.render_icon(area, target);
            }
            FuelGaugeMode::ChargingIconOnly => {
                if matches!(self.charging_state, ChargingState::Charging) {
                    self.render_icon(area, target);
                }
            }
            #[cfg(not(feature = "micropython"))]
            FuelGaugeMode::AlwaysFull => {
                self.render_icon_and_percentage(area, target);
            }
            #[cfg(feature = "micropython")]
            FuelGaugeMode::AlwaysFull | FuelGaugeMode::OnChargingChange(..) => {
                self.render_icon_and_percentage(area, target);
            }
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for FuelGauge {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("FuelGauge");
        t.int("soc", self.soc.unwrap_or(0) as i64);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn charging_icon_constant() {
        let gauge = FuelGauge::always();
        for soc in [0u8, 1, 50, 100] {
            let (icon, ic, tc) = gauge.battery_indication(ChargingState::Charging, soc);
            assert!(icon == ICON_BATTERY_ZAP);
            assert!(ic == YELLOW);
            assert!(tc == GREY_LIGHT);
        }
    }

    #[test]
    fn discharging_threshold_boundaries() {
        let gauge = FuelGauge::always();
        // soc, expected icon, icon color, text color
        let cases = [
            (9, ICON_BATTERY_EMPTY, RED, RED),
            (10, ICON_BATTERY_LOW, YELLOW, GREY_LIGHT),
            (19, ICON_BATTERY_LOW, YELLOW, GREY_LIGHT),
            (20, ICON_BATTERY_MID_MINUS, GREY_LIGHT, GREY_LIGHT),
            (39, ICON_BATTERY_MID_MINUS, GREY_LIGHT, GREY_LIGHT),
            (40, ICON_BATTERY_MID_PLUS, GREY_LIGHT, GREY_LIGHT),
            (89, ICON_BATTERY_MID_PLUS, GREY_LIGHT, GREY_LIGHT),
            (90, ICON_BATTERY_FULL, GREY_LIGHT, GREY_LIGHT),
        ];
        for (soc, exp_icon, exp_ic, exp_tc) in cases {
            let (icon, ic, tc) = gauge.battery_indication(ChargingState::Discharging, soc);
            assert!(icon == exp_icon, "icon soc={}", soc);
            assert!(ic == exp_ic, "icon color soc={}", soc);
            assert!(tc == exp_tc, "text color soc={}", soc);
        }
    }
}
