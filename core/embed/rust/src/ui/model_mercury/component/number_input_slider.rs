use super::{theme, Footer};
use crate::{
    strutil::{ShortString, TString},
    translations::TR,
    ui::{
        component::{Component, Event, EventCtx},
        constant::screen,
        display,
        event::TouchEvent,
        geometry::{Alignment, Alignment2D, Insets, Offset, Point, Rect},
        shape::{self, Renderer},
    },
};

pub enum NumberInputSliderDialogMsg {
    Changed(u16),
}

pub struct NumberInputSliderDialog {
    area: Rect,
    input: NumberInputSlider,
    footer: Footer<'static>,
    min: u16,
    max: u16,
    val: u16,
    init_val: u16,
}

impl NumberInputSliderDialog {
    pub fn new(min: u16, max: u16, init_value: u16) -> Self {
        Self {
            area: Rect::zero(),
            input: NumberInputSlider::new(min, max, init_value),
            footer: Footer::new::<TString<'static>>(
                TR::instructions__swipe_horizontally.into(),
                Some(TR::setting__adjust.into()),
            ),
            min,
            max,
            val: init_value,
            init_val: init_value,
        }
    }

    pub fn value(&self) -> u16 {
        self.input.value
    }
}

const INPUT_AREA_HEIGHT: i16 = 91;

impl Component for NumberInputSliderDialog {
    type Msg = NumberInputSliderDialogMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;

        let whole_area = self.area.inset(Insets::bottom(theme::SPACING));
        let (remaining, footer_area) = whole_area.split_bottom(self.footer.height());
        self.footer.place(footer_area);
        let content_area = remaining;

        let used_area = content_area
            .inset(Insets::sides(theme::SPACING))
            .inset(Insets::bottom(theme::SPACING));

        let input_area = Rect::snap(
            used_area.center(),
            Offset::new(used_area.width(), INPUT_AREA_HEIGHT),
            Alignment2D::CENTER,
        );

        self.input.place(input_area.inset(Insets::sides(20)));

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(value) = self.input.event(ctx, event) {
            self.val = value;

            if self.val == self.init_val || self.input.touching {
                self.footer
                    .update_instruction(ctx, TR::instructions__swipe_horizontally);
                self.footer.update_description(ctx, TR::setting__adjust);
                ctx.request_paint();
            } else {
                self.footer
                    .update_instruction(ctx, TR::instructions__swipe_up);
                self.footer.update_description(ctx, TR::setting__apply);
                ctx.request_paint();
            }

            return Some(Self::Msg::Changed(value));
        }
        None
    }

    fn paint(&mut self) {
        self.input.paint();
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.input.render(target);
        self.footer.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for NumberInputSliderDialog {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("NumberInputSliderDialog");
        t.child("input", &self.input);
    }
}

pub struct NumberInputSlider {
    area: Rect,
    touch_area: Rect,
    text_area: Rect,
    min: u16,
    max: u16,
    value: u16,
    touching: bool,
}

impl NumberInputSlider {
    pub fn new(min: u16, max: u16, value: u16) -> Self {
        let value = value.clamp(min, max);
        Self {
            area: Rect::zero(),
            touch_area: Rect::zero(),
            text_area: Rect::zero(),
            min,
            max,
            value,
            touching: false,
        }
    }

    pub fn touch_eval(
        &mut self,
        pos: Point,
        ctx: &mut EventCtx,
        force_bubble_up: bool,
    ) -> Option<u16> {
        if self.touching {
            let filled = pos.x - self.area.x0;
            let filled = filled.clamp(0, self.area.width());
            let val_pct = (filled as u16 * 100) / self.area.width() as u16;
            let val = (val_pct * (self.max - self.min)) / 100 + self.min;

            if val != self.value || force_bubble_up {
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
        self.touch_area = bounds.outset(Insets::new(0, 20, 0, 20)).clamp(screen());
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Touch(touch_event) = event {
            return match touch_event {
                TouchEvent::TouchStart(pos) => {
                    if self.touch_area.contains(pos) {
                        self.touching = true;
                        ctx.request_paint();
                    }
                    self.touch_eval(pos, ctx, true)
                }
                TouchEvent::TouchMove(pos) => self.touch_eval(pos, ctx, false),
                TouchEvent::TouchEnd(pos) => {
                    self.touching = false;
                    ctx.request_paint();
                    self.touch_eval(pos, ctx, true)
                }
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
        let (top_left_shape, top_right_shape, bot_left_shape, bot_right_shape) =
            shape::CornerHighlight::from_rect(
                self.area,
                if self.touching {
                    theme::GREY_DARK
                } else {
                    theme::WHITE
                },
                theme::BG,
            );
        top_left_shape.render(target);
        top_right_shape.render(target);
        bot_left_shape.render(target);
        bot_right_shape.render(target);

        let val_pct = (100 * (self.value - self.min)) / (self.max - self.min);

        let inner = self.area.inset(Insets::uniform(10));

        let fill_to = (val_pct as i16 * inner.width()) / 100;

        let inner = inner.with_width(fill_to as _);

        shape::Bar::new(inner)
            .with_radius(1)
            .with_bg(if self.touching {
                theme::WHITE
            } else {
                theme::GREY_EXTRA_DARK
            })
            .render(target);

        let mut str = ShortString::new();
        let val_pct = (100 * (self.value - self.min)) / (self.max - self.min);

        unwrap!(ufmt::uwrite!(str, "{} %", val_pct));

        if !self.touching {
            let text_height = theme::TEXT_BOLD.text_font.line_height();
            shape::Text::new(self.area.center() + Offset::new(0, text_height / 2), &str)
                .with_font(theme::TEXT_BOLD.text_font)
                .with_fg(theme::TEXT_BOLD.text_color)
                .with_align(Alignment::Center)
                .render(target);
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for NumberInputSlider {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("NumberInputSlider");
        t.int("value", self.value as i64);
    }
}
