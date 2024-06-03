use crate::{
    error::Error,
    strutil::{self, TString},
    ui::{
        component::{
            base::ComponentExt,
            paginated::Paginate,
            text::paragraphs::{Paragraph, Paragraphs},
            Child, Component, Event, EventCtx, Pad, SwipeDirection,
        },
        display::Font,
        flow::{Swipable, SwipableResult},
        geometry::{Alignment, Grid, Insets, Offset, Rect},
        shape::{self, Renderer},
    },
};

use super::{theme, Button, ButtonMsg};

pub struct NumberInputDialogMsg(pub u32);

pub struct NumberInputDialog<F>
where
    F: Fn(u32) -> TString<'static>,
{
    area: Rect,
    description_func: F,
    input: Child<NumberInput>,
    paragraphs: Child<Paragraphs<Paragraph<'static>>>,
    paragraphs_pad: Pad,
}

impl<F> NumberInputDialog<F>
where
    F: Fn(u32) -> TString<'static>,
{
    pub fn new(min: u32, max: u32, init_value: u32, description_func: F) -> Result<Self, Error> {
        let text = description_func(init_value);
        Ok(Self {
            area: Rect::zero(),
            description_func,
            input: NumberInput::new(min, max, init_value).into_child(),
            paragraphs: Paragraphs::new(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, text))
                .into_child(),
            paragraphs_pad: Pad::with_background(theme::BG),
        })
    }

    fn update_text(&mut self, ctx: &mut EventCtx, value: u32) {
        let text = (self.description_func)(value);
        self.paragraphs.mutate(ctx, move |ctx, para| {
            para.inner_mut().update(text);
            // Recompute bounding box.
            para.change_page(0);
            ctx.request_paint()
        });
        self.paragraphs_pad.clear();
        ctx.request_paint();
    }

    pub fn value(&self) -> u32 {
        self.input.inner().value
    }
}

impl<F> Component for NumberInputDialog<F>
where
    F: Fn(u32) -> TString<'static>,
{
    type Msg = NumberInputDialogMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        let bot_padding = 20;
        let top_padding = 14;
        let button_height = theme::COUNTER_BUTTON_HEIGHT;

        let content_area = self.area.inset(Insets::top(top_padding));
        let (content_area, input_area) = content_area.split_bottom(button_height + bot_padding);
        let input_area = input_area.inset(Insets::bottom(bot_padding));

        self.paragraphs.place(content_area);
        self.paragraphs_pad.place(content_area);
        self.input.place(input_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(NumberInputMsg::Changed(i)) = self.input.event(ctx, event) {
            self.update_text(ctx, i);
        }
        self.paragraphs.event(ctx, event);
        None
    }

    fn paint(&mut self) {
        todo!("remove when ui-t3t1 done");
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.input.render(target);
        self.paragraphs_pad.render(target);
        self.paragraphs.render(target);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area);
        self.input.bounds(sink);
        self.paragraphs.bounds(sink);
    }
}

impl<F> Swipable<NumberInputDialogMsg> for NumberInputDialog<F>
where
    F: Fn(u32) -> TString<'static>,
{
    fn swipe_start(
        &mut self,
        _ctx: &mut EventCtx,
        direction: SwipeDirection,
    ) -> SwipableResult<NumberInputDialogMsg> {
        match direction {
            SwipeDirection::Up => SwipableResult::Return(NumberInputDialogMsg(self.value())),
            _ => SwipableResult::Ignored,
        }
    }

    fn swipe_finished(&self) -> bool {
        true
    }
}

#[cfg(feature = "ui_debug")]
impl<F> crate::trace::Trace for NumberInputDialog<F>
where
    F: Fn(u32) -> TString<'static>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("NumberInputDialog");
        t.child("input", &self.input);
        t.child("paragraphs", &self.paragraphs);
    }
}

pub enum NumberInputMsg {
    Changed(u32),
}

pub struct NumberInput {
    area: Rect,
    dec: Child<Button>,
    inc: Child<Button>,
    min: u32,
    max: u32,
    value: u32,
}

impl NumberInput {
    pub fn new(min: u32, max: u32, value: u32) -> Self {
        let dec = Button::with_icon(theme::ICON_MINUS)
            .styled(theme::button_counter())
            .into_child();
        let inc = Button::with_icon(theme::ICON_PLUS)
            .styled(theme::button_counter())
            .into_child();
        let value = value.clamp(min, max);
        Self {
            area: Rect::zero(),
            dec,
            inc,
            min,
            max,
            value,
        }
    }
}

impl Component for NumberInput {
    type Msg = NumberInputMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let grid = Grid::new(bounds, 1, 3).with_spacing(theme::KEYBOARD_SPACING);
        self.dec.place(grid.row_col(0, 0));
        self.inc.place(grid.row_col(0, 2));
        self.area = grid.row_col(0, 1);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let mut changed = false;
        if let Some(ButtonMsg::Clicked) = self.dec.event(ctx, event) {
            self.value = self.min.max(self.value.saturating_sub(1));
            changed = true;
        };
        if let Some(ButtonMsg::Clicked) = self.inc.event(ctx, event) {
            self.value = self.max.min(self.value.saturating_add(1));
            changed = true;
        };
        if changed {
            self.dec
                .mutate(ctx, |ctx, btn| btn.enable_if(ctx, self.value > self.min));
            self.inc
                .mutate(ctx, |ctx, btn| btn.enable_if(ctx, self.value < self.max));
            ctx.request_paint();
            return Some(NumberInputMsg::Changed(self.value));
        }
        None
    }

    fn paint(&mut self) {
        todo!("remove when ui-t3t1 done");
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let mut buf = [0u8; 10];

        if let Some(text) = strutil::format_i64(self.value as i64, &mut buf) {
            let digit_font = Font::DEMIBOLD;
            let y_offset = digit_font.text_height() / 2;

            shape::Bar::new(self.area).with_bg(theme::BG).render(target);
            shape::Text::new(self.area.center() + Offset::y(y_offset), text)
                .with_align(Alignment::Center)
                .with_fg(theme::FG)
                .with_font(digit_font)
                .render(target);
        }

        self.dec.render(target);
        self.inc.render(target);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.dec.bounds(sink);
        self.inc.bounds(sink);
        sink(self.area)
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for NumberInput {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("NumberInput");
        t.int("value", self.value as i64);
    }
}
