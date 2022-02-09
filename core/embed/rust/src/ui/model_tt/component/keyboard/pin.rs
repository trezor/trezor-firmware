use core::ops::Deref;
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
        model_tt::component::{
            button::{Button, ButtonContent, ButtonMsg::Clicked},
            theme,
        },
    },
};

pub enum PinKeyboardMsg {
    Confirmed,
    Cancelled,
}

const MAX_LENGTH: usize = 9;
const DIGIT_COUNT: usize = 10; // 0..10

pub struct PinKeyboard<T> {
    digits: String<MAX_LENGTH>,
    allow_cancel: bool,
    major_prompt: Label<T>,
    minor_prompt: Label<T>,
    major_warning: Option<Label<T>>,
    dots: Child<PinDots>,
    reset_btn: Child<Maybe<Button<&'static str>>>,
    cancel_btn: Child<Maybe<Button<&'static str>>>,
    confirm_btn: Child<Button<&'static str>>,
    digit_btns: [Child<Button<&'static str>>; DIGIT_COUNT],
}

impl<T> PinKeyboard<T>
where
    T: Deref<Target = str>,
{
    const HEADER_HEIGHT: i32 = 25;
    const HEADER_PADDING_SIDE: i32 = 5;
    const HEADER_PADDING_BOTTOM: i32 = 12;

    // Label position fine-tuning.
    const MAJOR_OFF: Offset = Offset::y(-2);
    const MINOR_OFF: Offset = Offset::y(-1);

    pub fn new(
        major_prompt: T,
        minor_prompt: T,
        major_warning: Option<T>,
        allow_cancel: bool,
    ) -> Self {
        let digits = String::new();

        // Control buttons.
        let reset_btn = Button::with_icon(theme::ICON_BACK)
            .styled(theme::button_reset())
            .initially_enabled(false);
        let reset_btn = Maybe::hidden(theme::BG, reset_btn).into_child();

        let cancel_btn = Button::with_icon(theme::ICON_CANCEL).styled(theme::button_cancel());
        let cancel_btn =
            Maybe::new(Pad::with_background(theme::BG), cancel_btn, allow_cancel).into_child();

        Self {
            digits,
            allow_cancel,
            major_prompt: Label::left_aligned(major_prompt, theme::label_keyboard()),
            minor_prompt: Label::right_aligned(minor_prompt, theme::label_keyboard_minor()),
            major_warning: major_warning
                .map(|text| Label::left_aligned(text, theme::label_keyboard_warning())),
            dots: PinDots::new(0, theme::label_default()).into_child(),
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
        let is_full = self.digits.len() == self.digits.capacity();
        for btn in &mut self.digit_btns {
            btn.mutate(ctx, |ctx, btn| btn.enable_if(ctx, !is_full));
        }
        let is_empty = self.digits.is_empty();
        let cancel_enabled = is_empty && self.allow_cancel;
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
        let digit_count = self.digits.len();
        self.dots
            .mutate(ctx, |ctx, dots| dots.update(ctx, digit_count));
    }

    pub fn pin(&self) -> &str {
        &self.digits
    }
}

impl<T> Component for PinKeyboard<T>
where
    T: Deref<Target = str>,
{
    type Msg = PinKeyboardMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // Prompts and PIN dots display.
        let (header, keypad) = bounds
            .inset(theme::borders())
            .split_top(Self::HEADER_HEIGHT + Self::HEADER_PADDING_BOTTOM);
        let header = header.inset(Insets::new(
            0,
            Self::HEADER_PADDING_SIDE,
            Self::HEADER_PADDING_BOTTOM,
            Self::HEADER_PADDING_SIDE,
        ));
        let major_area = header.translate(Self::MAJOR_OFF);
        let minor_area = header.translate(Self::MINOR_OFF);

        // Control buttons.
        let grid = Grid::new(keypad, 4, 3).with_spacing(theme::KEYBOARD_SPACING);

        // Prompts and PIN dots display.
        self.dots.place(header);
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
        if let Some(Clicked) = self.confirm_btn.event(ctx, event) {
            return Some(PinKeyboardMsg::Confirmed);
        }
        if let Some(Clicked) = self.cancel_btn.event(ctx, event) {
            return Some(PinKeyboardMsg::Cancelled);
        }
        if let Some(Clicked) = self.reset_btn.event(ctx, event) {
            self.digits.clear();
            self.pin_modified(ctx);
            return None;
        }
        for btn in &mut self.digit_btns {
            if let Some(Clicked) = btn.event(ctx, event) {
                if let ButtonContent::Text(text) = btn.inner().content() {
                    if self.digits.push_str(text).is_err() {
                        // `self.pin` is full and wasn't able to accept all of
                        // `text`. Should not happen.
                    }
                    self.pin_modified(ctx);
                    return None;
                }
            }
        }
        None
    }

    fn paint(&mut self) {
        self.reset_btn.paint();
        if self.digits.is_empty() {
            self.dots.inner().clear();
            if let Some(ref mut w) = self.major_warning {
                w.paint();
            } else {
                self.major_prompt.paint();
            }
            self.minor_prompt.paint();
            self.cancel_btn.paint();
        } else {
            self.dots.paint();
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
        self.dots.bounds(sink);
        for b in &self.digit_btns {
            b.bounds(sink)
        }
    }
}

struct PinDots {
    area: Rect,
    style: LabelStyle,
    digit_count: usize,
}

impl PinDots {
    const DOT: i32 = 6;
    const PADDING: i32 = 4;

    fn new(digit_count: usize, style: LabelStyle) -> Self {
        Self {
            style,
            digit_count,
            area: Rect::zero(),
        }
    }

    fn update(&mut self, ctx: &mut EventCtx, digit_count: usize) {
        if self.digit_count != digit_count {
            self.digit_count = digit_count;
            ctx.request_paint();
        }
    }

    /// Clear the area with the background color.
    fn clear(&self) {
        display::rect_fill(self.area, self.style.background_color);
    }

    fn size(&self) -> Offset {
        let mut width = Self::DOT * (self.digit_count as i32);
        width += Self::PADDING * (self.digit_count.saturating_sub(1) as i32);
        Offset::new(width, Self::DOT)
    }
}

impl Component for PinDots {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.clear();

        let mut cursor = self
            .size()
            .snap(self.area.center(), Alignment::Center, Alignment::Center);

        // Draw a dot for each PIN digit.
        for _ in 0..self.digit_count {
            display::icon_top_left(
                cursor,
                theme::DOT_ACTIVE,
                self.style.text_color,
                self.style.background_color,
            );
            cursor.x += Self::DOT + Self::PADDING;
        }
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area);
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
