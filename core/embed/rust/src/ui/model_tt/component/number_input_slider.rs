use crate::ui::{
    component::{base::ComponentExt, Child, Component, Event, EventCtx},
    constant::screen,
    display,
    event::TouchEvent,
    geometry::{Grid, Insets, Point, Rect},
};

use super::{theme, Button, ButtonMsg};

pub enum NumberInputSliderDialogMsg {
    Confirmed,
    Cancelled,
}

pub struct NumberInputSliderDialog<F>
where
    F: Fn(u32),
{
    area: Rect,
    callback: F,
    input: Child<NumberInputSlider>,
    cancel_button: Child<Button>,
    confirm_button: Child<Button>,
}

impl<F> NumberInputSliderDialog<F>
where
    F: Fn(u32),
{
    pub fn new(min: u32, max: u32, init_value: u32, callback: F) -> Self {
        Self {
            area: Rect::zero(),
            callback,
            input: NumberInputSlider::new(min, max, init_value).into_child(),
            cancel_button: Button::with_text("CANCEL".into())
                .styled(theme::button_cancel())
                .into_child(),
            confirm_button: Button::with_text("CONFIRM".into())
                .styled(theme::button_confirm())
                .into_child(),
        }
    }

    pub fn value(&self) -> u32 {
        self.input.inner().value
    }
}

impl<F> Component for NumberInputSliderDialog<F>
where
    F: Fn(u32),
{
    type Msg = NumberInputSliderDialogMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        let button_height = theme::BUTTON_HEIGHT;
        let content_area = self.area.inset(Insets::top(2 * theme::BUTTON_SPACING));
        let (_, content_area) = content_area.split_top(30);
        let (input_area, _) = content_area.split_top(15);
        let (_, button_area) = content_area.split_bottom(button_height);
        // let (content_area, button_area) = content_area.split_bottom(button_height);
        // let content_area = content_area.inset(Insets::new(
        //     theme::BUTTON_SPACING,
        //     0,
        //     theme::BUTTON_SPACING,
        //     theme::CONTENT_BORDER,
        // ));

        let grid = Grid::new(button_area, 1, 2).with_spacing(theme::KEYBOARD_SPACING);
        self.input.place(input_area.inset(Insets::sides(20)));
        self.cancel_button.place(grid.row_col(0, 0));
        self.confirm_button.place(grid.row_col(0, 1));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(NumberInputSliderMsg::Changed(i)) = self.input.event(ctx, event) {
            (self.callback)(i);
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
        // self.paragraphs_pad.paint();
        // self.paragraphs.paint();
        self.cancel_button.paint();
        self.confirm_button.paint();
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area);
        self.input.bounds(sink);
        // self.paragraphs.bounds(sink);
        self.cancel_button.bounds(sink);
        self.confirm_button.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl<F> crate::trace::Trace for NumberInputSliderDialog<F>
where
    F: Fn(u32),
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("NumberInputSliderDialog");
        t.child("input", &self.input);
        t.child("cancel_button", &self.cancel_button);
        t.child("confirm_button", &self.confirm_button);
    }
}

pub enum NumberInputSliderMsg {
    Changed(u32),
}

pub struct NumberInputSlider {
    area: Rect,
    touch_area: Rect,
    min: u32,
    max: u32,
    value: u32,
}

impl NumberInputSlider {
    pub fn new(min: u32, max: u32, value: u32) -> Self {
        let value = value.clamp(min, max);
        Self {
            area: Rect::zero(),
            touch_area: Rect::zero(),
            min,
            max,
            value,
        }
    }

    pub fn slider_eval(&mut self, pos: Point, ctx: &mut EventCtx) -> Option<NumberInputSliderMsg> {
        if self.touch_area.contains(pos) {
            let filled = pos.x - self.area.x0;
            let filled = filled.clamp(0, self.area.width());
            let val_pct = (filled as u32 * 100) / self.area.width() as u32;
            let val = (val_pct * (self.max - self.min)) / 100 + self.min;

            if val != self.value {
                self.value = val;
                ctx.request_paint();
                return Some(NumberInputSliderMsg::Changed(self.value));
            }
        }
        None
    }
}

impl Component for NumberInputSlider {
    type Msg = NumberInputSliderMsg;

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
            };
        }
        None
    }

    fn paint(&mut self) {
        let val_pct = (100 * (self.value - self.min)) / (self.max - self.min);
        let fill_to = (val_pct as i16 * self.area.width()) / 100;

        display::bar_with_text_and_fill(self.area, None, theme::FG, theme::BG, 0, fill_to as _);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area)
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for NumberInputSlider {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("NumberInput");
        t.int("value", self.value as i64);
    }
}
