use crate::{
    error::Error,
    micropython::buffer::StrBuffer,
    strutil::{self, StringType},
    translations::TR,
    ui::{
        component::{
            base::ComponentExt,
            paginated::Paginate,
            text::paragraphs::{Paragraph, Paragraphs},
            Child, Component, Event, EventCtx, Pad,
        },
        display::{self, Font},
        geometry::{Grid, Insets, Offset, Rect},
    },
};

use super::{theme, Button, ButtonMsg};

pub enum NumberInputDialogMsg {
    Selected,
    InfoRequested,
}

pub struct NumberInputDialog<T, F>
where
    F: Fn(u32) -> T,
{
    area: Rect,
    description_func: F,
    input: Child<NumberInput>,
    paragraphs: Child<Paragraphs<Paragraph<T>>>,
    paragraphs_pad: Pad,
    info_button: Child<Button<StrBuffer>>,
    confirm_button: Child<Button<StrBuffer>>,
}

impl<T, F> NumberInputDialog<T, F>
where
    F: Fn(u32) -> T,
    T: StringType,
{
    pub fn new(min: u32, max: u32, init_value: u32, description_func: F) -> Result<Self, Error> {
        let text = description_func(init_value);
        Ok(Self {
            area: Rect::zero(),
            description_func,
            input: NumberInput::new(min, max, init_value).into_child(),
            paragraphs: Paragraphs::new(Paragraph::new(&theme::TEXT_NORMAL, text)).into_child(),
            paragraphs_pad: Pad::with_background(theme::BG),
            info_button: Button::with_text(TR::buttons__info.try_into()?).into_child(),
            confirm_button: Button::with_text(TR::buttons__continue.try_into()?)
                .styled(theme::button_confirm())
                .into_child(),
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

impl<T, F> Component for NumberInputDialog<T, F>
where
    T: StringType,
    F: Fn(u32) -> T,
{
    type Msg = NumberInputDialogMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        let button_height = theme::BUTTON_HEIGHT;
        let content_area = self.area.inset(Insets::top(2 * theme::BUTTON_SPACING));
        let (input_area, content_area) = content_area.split_top(button_height);
        let (content_area, button_area) = content_area.split_bottom(button_height);
        let content_area = content_area.inset(Insets::new(
            theme::BUTTON_SPACING,
            0,
            theme::BUTTON_SPACING,
            theme::CONTENT_BORDER,
        ));

        let grid = Grid::new(button_area, 1, 2).with_spacing(theme::KEYBOARD_SPACING);
        self.input.place(input_area);
        self.paragraphs.place(content_area);
        self.paragraphs_pad.place(content_area);
        self.info_button.place(grid.row_col(0, 0));
        self.confirm_button.place(grid.row_col(0, 1));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(NumberInputMsg::Changed(i)) = self.input.event(ctx, event) {
            self.update_text(ctx, i);
        }
        self.paragraphs.event(ctx, event);
        if let Some(ButtonMsg::Clicked) = self.info_button.event(ctx, event) {
            return Some(Self::Msg::InfoRequested);
        }
        if let Some(ButtonMsg::Clicked) = self.confirm_button.event(ctx, event) {
            return Some(Self::Msg::Selected);
        };
        None
    }

    fn paint(&mut self) {
        self.input.paint();
        self.paragraphs_pad.paint();
        self.paragraphs.paint();
        self.info_button.paint();
        self.confirm_button.paint();
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area);
        self.input.bounds(sink);
        self.paragraphs.bounds(sink);
        self.info_button.bounds(sink);
        self.confirm_button.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl<T, F> crate::trace::Trace for NumberInputDialog<T, F>
where
    T: StringType,
    F: Fn(u32) -> T,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("NumberInputDialog");
        t.child("input", &self.input);
        t.child("paragraphs", &self.paragraphs);
        t.child("info_button", &self.info_button);
        t.child("confirm_button", &self.confirm_button);
    }
}

pub enum NumberInputMsg {
    Changed(u32),
}

pub struct NumberInput {
    area: Rect,
    dec: Child<Button<&'static str>>,
    inc: Child<Button<&'static str>>,
    min: u32,
    max: u32,
    value: u32,
}

impl NumberInput {
    pub fn new(min: u32, max: u32, value: u32) -> Self {
        let dec = Button::with_text("-")
            .styled(theme::button_counter())
            .into_child();
        let inc = Button::with_text("+")
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
        let mut buf = [0u8; 10];
        if let Some(text) = strutil::format_i64(self.value as i64, &mut buf) {
            let digit_font = Font::DEMIBOLD;
            let y_offset = digit_font.text_height() / 2 + Button::<&str>::BASELINE_OFFSET;
            display::rect_fill(self.area, theme::BG);
            display::text_center(
                self.area.center() + Offset::y(y_offset),
                text,
                digit_font,
                theme::FG,
                theme::BG,
            );
        }
        self.dec.paint();
        self.inc.paint();
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
