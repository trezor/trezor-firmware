use core::{mem, ops::Deref};
use heapless::String;

use crate::{
    trezorhal::random,
    ui::{
        component::{
            base::ComponentExt, Child, Component, Event, EventCtx, Label, LabelStyle, Maybe, Never,
            Pad,
        },
        display,
        geometry::{Alignment, Grid, Insets, Offset, Rect},
        model_tt::{
            component::{
                button::{Button, ButtonContent, ButtonMsg::Clicked},
                theme,
            },
            event::TouchEvent,
        },
    },
};

pub enum PinKeyboardMsg {
    Confirmed,
    Cancelled,
}

const MAX_LENGTH: usize = 9;
const DIGIT_COUNT: usize = 10; // 0..10

const HEADER_HEIGHT: i32 = 25;
const HEADER_PADDING_SIDE: i32 = 5;
const HEADER_PADDING_BOTTOM: i32 = 12;

const HEADER_PADDING: Insets = Insets::new(
    theme::borders().top,
    HEADER_PADDING_SIDE,
    HEADER_PADDING_BOTTOM,
    HEADER_PADDING_SIDE,
);

pub struct PinKeyboard<T> {
    allow_cancel: bool,
    major_prompt: Label<T>,
    minor_prompt: Label<T>,
    major_warning: Option<Label<T>>,
    textbox: Child<PinDots>,
    reset_btn: Child<Maybe<Button<&'static str>>>,
    cancel_btn: Child<Maybe<Button<&'static str>>>,
    confirm_btn: Child<Button<&'static str>>,
    digit_btns: [Child<Button<&'static str>>; DIGIT_COUNT],
}

impl<T> PinKeyboard<T>
where
    T: Deref<Target = str>,
{
    // Label position fine-tuning.
    const MAJOR_OFF: Offset = Offset::y(-2);
    const MINOR_OFF: Offset = Offset::y(-1);

    pub fn new(
        major_prompt: T,
        minor_prompt: T,
        major_warning: Option<T>,
        allow_cancel: bool,
    ) -> Self {
        // Control buttons.
        let reset_btn = Button::with_icon(theme::ICON_BACK)
            .styled(theme::button_reset())
            .initially_enabled(false);
        let reset_btn = Maybe::hidden(theme::BG, reset_btn).into_child();

        let cancel_btn = Button::with_icon(theme::ICON_CANCEL).styled(theme::button_cancel());
        let cancel_btn =
            Maybe::new(Pad::with_background(theme::BG), cancel_btn, allow_cancel).into_child();

        Self {
            allow_cancel,
            major_prompt: Label::left_aligned(major_prompt, theme::label_keyboard()),
            minor_prompt: Label::right_aligned(minor_prompt, theme::label_keyboard_minor()),
            major_warning: major_warning
                .map(|text| Label::left_aligned(text, theme::label_keyboard_warning())),
            textbox: PinDots::new(theme::label_default()).into_child(),
            reset_btn,
            cancel_btn,
            confirm_btn: Button::with_icon(theme::ICON_CONFIRM)
                .styled(theme::button_confirm())
                .initially_enabled(false)
                .into_child(),
            digit_btns: Self::generate_digit_buttons(),
        }
    }

    fn generate_digit_buttons() -> [Child<Button<&'static str>>; DIGIT_COUNT] {
        // Generate a random sequence of digits from 0 to 9.
        let mut digits = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"];
        random::shuffle(&mut digits);
        digits
            .map(Button::with_text)
            .map(|b| b.styled(theme::button_pin()))
            .map(Child::new)
    }

    fn pin_modified(&mut self, ctx: &mut EventCtx) {
        let is_full = self.textbox.inner().is_full();
        let is_empty = self.textbox.inner().is_empty();
        let cancel_enabled = is_empty && self.allow_cancel;
        for btn in &mut self.digit_btns {
            btn.mutate(ctx, |ctx, btn| btn.enable_if(ctx, !is_full));
        }
        self.reset_btn.mutate(ctx, |ctx, btn| {
            btn.show_if(ctx, !is_empty);
            btn.inner_mut().enable_if(ctx, !is_empty);
        });
        self.cancel_btn.mutate(ctx, |ctx, btn| {
            btn.show_if(ctx, cancel_enabled);
            btn.inner_mut().enable_if(ctx, is_empty);
        });
        self.confirm_btn
            .mutate(ctx, |ctx, btn| btn.enable_if(ctx, !is_empty));
    }

    pub fn pin(&self) -> &str {
        &self.textbox.inner().pin()
    }
}

impl<T> Component for PinKeyboard<T>
where
    T: Deref<Target = str>,
{
    type Msg = PinKeyboardMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // Ignore the top padding for now, we need it to reliably register textbox touch events.
        let borders_no_top = Insets {
            top: 0,
            ..theme::borders()
        };
        // Prompts and PIN dots display.
        let (header, keypad) = bounds
            .inset(borders_no_top)
            .split_top(theme::borders().top + HEADER_HEIGHT + HEADER_PADDING_BOTTOM);
        let prompt = header.inset(HEADER_PADDING);
        let major_area = prompt.translate(Self::MAJOR_OFF);
        let minor_area = prompt.translate(Self::MINOR_OFF);

        // Control buttons.
        let grid = Grid::new(keypad, 4, 3).with_spacing(theme::KEYBOARD_SPACING);

        // Prompts and PIN dots display.
        self.textbox.place(header);
        self.major_prompt.place(major_area);
        self.minor_prompt.place(minor_area);
        self.major_warning.as_mut().map(|c| c.place(major_area));

        // Control buttons.
        let reset_cancel_area = grid.row_col(3, 0);
        self.reset_btn.place(reset_cancel_area);
        self.cancel_btn.place(reset_cancel_area);
        self.confirm_btn.place(grid.row_col(3, 2));

        // Digit buttons.
        for (i, btn) in self.digit_btns.iter_mut().enumerate() {
            // Assign the digits to buttons on a 4x3 grid, starting from the first row.
            let area = grid.cell(if i < 9 {
                i
            } else {
                // For the last key (the "0" position) we skip one cell.
                i + 1
            });
            btn.place(area);
        }

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.textbox.event(ctx, event);
        if let Some(Clicked) = self.confirm_btn.event(ctx, event) {
            return Some(PinKeyboardMsg::Confirmed);
        }
        if let Some(Clicked) = self.cancel_btn.event(ctx, event) {
            return Some(PinKeyboardMsg::Cancelled);
        }
        if let Some(Clicked) = self.reset_btn.event(ctx, event) {
            self.textbox.mutate(ctx, |ctx, t| t.clear(ctx));
            self.pin_modified(ctx);
            return None;
        }
        for btn in &mut self.digit_btns {
            if let Some(Clicked) = btn.event(ctx, event) {
                if let ButtonContent::Text(text) = btn.inner().content() {
                    self.textbox.mutate(ctx, |ctx, t| t.push(ctx, text));
                    self.pin_modified(ctx);
                    return None;
                }
            }
        }
        None
    }

    fn paint(&mut self) {
        self.reset_btn.paint();
        if self.textbox.inner().is_empty() {
            self.textbox.inner().clear_background();
            if let Some(ref mut w) = self.major_warning {
                w.paint();
            } else {
                self.major_prompt.paint();
            }
            self.minor_prompt.paint();
            self.cancel_btn.paint();
        } else {
            self.textbox.paint();
        }
        self.confirm_btn.paint();
        for btn in &mut self.digit_btns {
            btn.paint();
        }
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.major_prompt.bounds(sink);
        self.minor_prompt.bounds(sink);
        self.reset_btn.bounds(sink);
        self.cancel_btn.bounds(sink);
        self.confirm_btn.bounds(sink);
        self.textbox.bounds(sink);
        for b in &self.digit_btns {
            b.bounds(sink)
        }
    }
}

struct PinDots {
    area: Rect,
    style: LabelStyle,
    digits: String<MAX_LENGTH>,
    display_digits: bool,
}

impl PinDots {
    const DOT: i32 = 6;
    const PADDING: i32 = 4;

    fn new(style: LabelStyle) -> Self {
        Self {
            area: Rect::zero(),
            style,
            digits: String::new(),
            display_digits: false,
        }
    }

    /// Clear the area with the background color.
    fn clear_background(&self) {
        display::rect_fill(self.area, self.style.background_color);
    }

    fn size(&self) -> Offset {
        let digit_count = self.digits.len();
        let mut width = Self::DOT * (digit_count as i32);
        width += Self::PADDING * (digit_count.saturating_sub(1) as i32);
        Offset::new(width, Self::DOT)
    }

    fn is_empty(&self) -> bool {
        self.digits.is_empty()
    }

    fn is_full(&self) -> bool {
        self.digits.len() == self.digits.capacity()
    }

    fn clear(&mut self, ctx: &mut EventCtx) {
        self.digits.clear();
        ctx.request_paint()
    }

    fn push(&mut self, ctx: &mut EventCtx, text: &str) {
        if self.digits.push_str(text).is_err() {
            // `self.pin` is full and wasn't able to accept all of
            // `text`. Should not happen.
        };
        ctx.request_paint()
    }

    fn pop(&mut self, ctx: &mut EventCtx) {
        if self.digits.pop().is_some() {
            ctx.request_paint()
        }
    }

    fn pin(&self) -> &str {
        &self.digits
    }

    fn paint_digits(&self, area: Rect) {
        let center = area.center() + Offset::y(theme::FONT_MONO.text_height() / 2);
        display::text_center(
            center,
            &self.digits,
            theme::FONT_MONO,
            self.style.text_color,
            self.style.background_color,
        );
    }

    fn paint_dots(&self, area: Rect) {
        let mut cursor = self
            .size()
            .snap(area.center(), Alignment::Center, Alignment::Center);

        // Draw a dot for each PIN digit.
        for _ in 0..self.digits.len() {
            display::icon_top_left(
                cursor,
                theme::DOT_ACTIVE,
                self.style.text_color,
                self.style.background_color,
            );
            cursor.x += Self::DOT + Self::PADDING;
        }
    }
}

impl Component for PinDots {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            Event::Touch(TouchEvent::TouchStart(pos)) => {
                if self.area.contains(pos) {
                    self.display_digits = true;
                    ctx.request_paint();
                };
                None
            }
            Event::Touch(TouchEvent::TouchEnd(_)) => {
                if mem::replace(&mut self.display_digits, false) {
                    ctx.request_paint();
                };
                None
            }
            _ => None,
        }
    }

    fn paint(&mut self) {
        self.clear_background();
        let dot_area = self.area.inset(HEADER_PADDING);

        if self.display_digits {
            self.paint_digits(dot_area)
        } else {
            self.paint_dots(dot_area)
        }
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area);
        sink(self.area.inset(HEADER_PADDING));
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for PinKeyboard<T>
where
    T: Deref<Target = str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("PinKeyboard");
        t.close();
    }
}
