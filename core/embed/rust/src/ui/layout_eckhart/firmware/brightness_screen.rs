use crate::{
    storage,
    translations::TR,
    trezorhal::display,
    ui::{
        component::{Component, Event, EventCtx},
        event::TouchEvent,
        geometry::{Alignment2D, Insets, Offset, Point, Rect},
        shape::{Bar, Renderer},
    },
};

use super::super::{
    constant::SCREEN,
    firmware::{Header, HeaderMsg},
    theme,
};

pub struct SetBrightnessScreen {
    header: Header,
    slider: VerticalSlider,
}

impl SetBrightnessScreen {
    const SLIDER_HEIGHT: i16 = 392;
    pub fn new(min: u16, max: u16, init_value: u16) -> Self {
        Self {
            header: Header::new(TR::brightness__title.into()).with_close_button(),
            slider: VerticalSlider::new(min, max, init_value),
        }
    }
}

impl Component for SetBrightnessScreen {
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (header_area, rest) = bounds.split_top(Header::HEADER_HEIGHT);
        let (slider_area, _) = rest.split_top(Self::SLIDER_HEIGHT);

        self.header.place(header_area);
        self.slider.place(slider_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(HeaderMsg::Cancelled) = self.header.event(ctx, event) {
            return Some(());
        }

        if let Some(value) = self.slider.event(ctx, event) {
            unwrap!(storage::set_brightness(value as _));
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.slider.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for SetBrightnessScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("SetBrightnessScreen");
        t.child("Header", &self.header);
        t.child("Slider", &self.slider);
    }
}

struct VerticalSlider {
    area: Rect,
    touch_area: Rect,
    min: u16,
    max: u16,
    value: u16,
    val_pct: u16,
    touching: bool,
}

impl VerticalSlider {
    const SLIDER_WIDTH: i16 = 120;

    pub fn new(min: u16, max: u16, value: u16) -> Self {
        debug_assert!(min < max);
        let value = value.clamp(min, max);
        Self {
            area: Rect::zero(),
            touch_area: Rect::zero(),
            min,
            max,
            value,
            val_pct: 0,
            touching: false,
        }
    }

    pub fn update_value(&mut self, pos: Point, ctx: &mut EventCtx) {
        // Area where slider value is not saturated
        let proportional_area = self.area.inset(Insets::new(
            Self::SLIDER_WIDTH / 2,
            0,
            Self::SLIDER_WIDTH / 2,
            0,
        ));

        let filled = (proportional_area.y1 - pos.y).clamp(0, proportional_area.height());
        let val_pct = (filled as u16 * 100) / proportional_area.height() as u16;
        let val = (val_pct * (self.max - self.min)) / 100 + self.min;

        if val != self.value {
            ctx.request_paint();
            self.value = val;
        }
    }
}

impl Component for VerticalSlider {
    type Msg = u8;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = Rect::snap(
            bounds.center(),
            Offset::new(Self::SLIDER_WIDTH, bounds.height()),
            Alignment2D::CENTER,
        );
        self.touch_area = self.area.outset(Insets::uniform(30));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Touch(touch_event) = event {
            match touch_event {
                TouchEvent::TouchStart(pos) if self.touch_area.contains(pos) => {
                    // Detect only touches inside the touch area
                    self.touching = true;
                    self.update_value(pos, ctx);
                    display::backlight(self.value as _);
                    ctx.request_paint();
                }
                TouchEvent::TouchMove(pos) if self.touching => {
                    self.update_value(pos, ctx);
                    // Update only if the touch started inside the touch area
                    display::backlight(self.value as _);
                }
                TouchEvent::TouchEnd(pos) if self.touching => {
                    self.touching = false;
                    self.update_value(pos, ctx);
                    ctx.request_paint();
                    return Some(self.value as _);
                }
                _ => {}
            };
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let val_pct = ((100 * (self.value - self.min)) / (self.max - self.min)).clamp(0, 100);

        // Square area for the slider
        let (_, small_area) = self.area.split_bottom(Self::SLIDER_WIDTH);

        // Background pad
        Bar::new(self.area)
            .with_radius(12)
            .with_bg(theme::GREY_EXTRA_DARK)
            .render(target);

        let slider_color = if self.touching {
            theme::GREY
        } else {
            theme::GREY_LIGHT
        };

        // Moving slider
        Bar::new(small_area.translate(
            Offset::y(val_pct as i16 * (self.area.height() - Self::SLIDER_WIDTH) / 100).neg(),
        ))
        .with_radius(4)
        .with_bg(slider_color)
        .render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for VerticalSlider {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("VerticalSlider");
        t.int("value", self.value as i64);
    }
}

#[cfg(test)]
mod tests {
    use super::{super::super::constant::SCREEN, *};

    #[test]
    fn test_component_heights_fit_screen() {
        assert!(
            SetBrightnessScreen::SLIDER_HEIGHT + Header::HEADER_HEIGHT <= SCREEN.height(),
            "Components overflow the screen height",
        );
    }
}
