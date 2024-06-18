use crate::{
    strutil::ShortString,
    ui::{
        component::{base::ComponentExt, Child, Component, Event, EventCtx},
        constant::screen,
        display,
        event::TouchEvent,
        geometry::{Alignment, Grid, Insets, Point, Rect},
        shape::{self, Renderer},
    },
};

use super::{theme, Button, ButtonMsg};

pub enum NumberInputSliderDialogMsg {
    Changed(u16),
    Confirmed,
    Cancelled,
}

pub struct NumberInputSliderDialog {
    area: Rect,
    text_area: Rect,
    input: Child<NumberInputSlider>,
    cancel_button: Child<Button>,
    confirm_button: Child<Button>,
    min: u16,
    max: u16,
    val: u16,
}

impl NumberInputSliderDialog {
    pub fn new(min: u16, max: u16, init_value: u16) -> Self {
        Self {
            area: Rect::zero(),
            text_area: Rect::zero(),
            input: NumberInputSlider::new(min, max, init_value).into_child(),
            cancel_button: Button::with_text("CANCEL".into())
                .styled(theme::button_cancel())
                .into_child(),
            confirm_button: Button::with_text("CONFIRM".into())
                .styled(theme::button_confirm())
                .into_child(),
            min,
            max,
            val: init_value,
        }
    }

    pub fn value(&self) -> u16 {
        self.input.inner().value
    }
}

impl Component for NumberInputSliderDialog {
    type Msg = NumberInputSliderDialogMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        let button_height = theme::BUTTON_HEIGHT;
        let content_area = self.area.inset(Insets::top(2 * theme::BUTTON_SPACING));
        let (_, content_area) = content_area.split_top(30);
        let (input_area, _) = content_area.split_top(15);
        let (text_area, button_area) = content_area.split_bottom(button_height);

        self.text_area = text_area;

        let grid = Grid::new(button_area, 1, 2).with_spacing(theme::KEYBOARD_SPACING);
        self.input.place(input_area.inset(Insets::sides(20)));
        self.cancel_button.place(grid.row_col(0, 0));
        self.confirm_button.place(grid.row_col(0, 1));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(value) = self.input.event(ctx, event) {
            self.val = value;
            return Some(Self::Msg::Changed(value));
        }
        if let Some(ButtonMsg::Clicked) = self.cancel_button.event(ctx, event) {
            return Some(Self::Msg::Cancelled);
        }
        if let Some(ButtonMsg::Clicked) = self.confirm_button.event(ctx, event) {
            return Some(Self::Msg::Confirmed);
        };
        None
    }

    fn paint(&mut self) {
        self.input.paint();
        self.cancel_button.paint();
        self.confirm_button.paint();
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.input.render(target);

        let mut str = ShortString::new();
        let val_pct = (100 * (self.val - self.min)) / (self.max - self.min);

        unwrap!(ufmt::uwrite!(str, "{} %", val_pct));

        shape::Text::new(self.text_area.center(), &str)
            .with_font(theme::TEXT_NORMAL.text_font)
            .with_fg(theme::TEXT_NORMAL.text_color)
            .with_align(Alignment::Center)
            .render(target);

        self.cancel_button.render(target);
        self.confirm_button.render(target);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area);
        self.input.bounds(sink);
        self.cancel_button.bounds(sink);
        self.confirm_button.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for NumberInputSliderDialog {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("NumberInputSliderDialog");
        t.child("input", &self.input);
        t.child("cancel_button", &self.cancel_button);
        t.child("confirm_button", &self.confirm_button);
    }
}

pub struct NumberInputSlider {
    area: Rect,
    touch_area: Rect,
    min: u16,
    max: u16,
    value: u16,
}

impl NumberInputSlider {
    pub fn new(min: u16, max: u16, value: u16) -> Self {
        let value = value.clamp(min, max);
        Self {
            area: Rect::zero(),
            touch_area: Rect::zero(),
            min,
            max,
            value,
        }
    }

    pub fn slider_eval(&mut self, pos: Point, ctx: &mut EventCtx) -> Option<u16> {
        if self.touch_area.contains(pos) {
            let filled = pos.x - self.area.x0;
            let filled = filled.clamp(0, self.area.width());
            let val_pct = (filled as u16 * 100) / self.area.width() as u16;
            let val = (val_pct * (self.max - self.min)) / 100 + self.min;

            if val != self.value {
                self.value = val;
                ctx.request_paint();
                return Some(self.value);
            }
        }
        None
    }
}

impl Component for NumberInputSlider {
    type Msg = u16;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.touch_area = bounds.outset(Insets::new(40, 20, 40, 20)).clamp(screen());
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Touch(touch_event) = event {
            return match touch_event {
                TouchEvent::TouchStart(pos) => self.slider_eval(pos, ctx),
                TouchEvent::TouchMove(pos) => self.slider_eval(pos, ctx),
                TouchEvent::TouchEnd(pos) => self.slider_eval(pos, ctx),
                TouchEvent::TouchAbort => None,
            };
        }
        None
    }

    fn paint(&mut self) {
        let val_pct = (100 * (self.value - self.min)) / (self.max - self.min);
        let fill_to = (val_pct as i16 * self.area.width()) / 100;

        display::bar_with_text_and_fill(self.area, None, theme::FG, theme::BG, 0, fill_to as _);
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let val_pct = (100 * (self.value - self.min)) / (self.max - self.min);

        shape::Bar::new(self.area)
            .with_radius(2)
            .with_thickness(2)
            .with_bg(theme::BG)
            .with_fg(theme::FG)
            .render(target);

        let inner = self.area.inset(Insets::uniform(1));

        let fill_to = (val_pct as i16 * inner.width()) / 100;

        let inner = inner.with_width(fill_to as _);

        shape::Bar::new(inner)
            .with_radius(1)
            .with_bg(theme::FG)
            .render(target);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area)
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for NumberInputSlider {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("NumberInputSlider");
        t.int("value", self.value as i64);
    }
}
