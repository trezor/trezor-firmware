use core::ops::Deref;
use heapless::Vec;

use crate::{
    trezorhal::random,
    ui::{
        component::{
            base::ComponentExt,
            label::{Label, LabelStyle},
            Child, Component, Event, EventCtx, Never,
        },
        display::{self, Color},
        geometry::{Alignment, Grid, Insets, Offset, Rect},
    },
};

use super::{
    button::{Button, ButtonContent, ButtonMsg::Clicked},
    theme,
};

pub enum PinDialogMsg {
    Confirmed,
    Cancelled,
}

const MAX_LENGTH: usize = 9;
const DIGIT_COUNT: usize = 10; // 0..10

const BUTTON_SPACING: i32 = 8;
const HEADER_HEIGHT: i32 = 25;
const HEADER_PADDING_SIDE: i32 = 5;
const HEADER_PADDING_BOTTOM: i32 = 12;

// Label position fine-tuning.
const MAJOR_OFF: Offset = Offset::y(-2);
const MINOR_OFF: Offset = Offset::y(-1);

pub struct PinDialog<T> {
    digits: Vec<u8, MAX_LENGTH>,
    allow_cancel: bool,
    major_prompt: Label<T>,
    minor_prompt: Label<T>,
    dots: Child<PinDots>,
    reset_btn: Child<Button<&'static str>>,
    cancel_btn: Child<Button<&'static str>>,
    confirm_btn: Child<Button<&'static str>>,
    digit_btns: [Child<Button<&'static str>>; DIGIT_COUNT],
}

impl<T> PinDialog<T>
where
    T: Deref<Target = [u8]>,
{
    pub fn new(
        area: Rect,
        major_prompt: T,
        minor_prompt: T,
        major_color: Color,
        minor_color: Color,
        allow_cancel: bool,
    ) -> Self {
        let area = area.inset(Insets::right(theme::CONTENT_BORDER));
        let digits = Vec::new();

        // Prompts and PIN dots display.
        let (header, keypad) = area.split_top(HEADER_HEIGHT + HEADER_PADDING_BOTTOM);
        let header = header.inset(Insets::new(
            0,
            HEADER_PADDING_SIDE,
            HEADER_PADDING_BOTTOM,
            HEADER_PADDING_SIDE,
        ));

        let major_prompt = Label::left_aligned(
            header.top_left() + MAJOR_OFF,
            major_prompt,
            theme::label_medium(),
        )
        .with_text_color(major_color);
        let minor_prompt = Label::right_aligned(
            header.top_right() + MINOR_OFF,
            minor_prompt,
            theme::label_default(),
        )
        .with_text_color(minor_color);
        let dots = PinDots::new(header, digits.len(), theme::label_default()).into_child();

        // Control buttons.
        let grid = Grid::new(keypad, 4, 3).with_spacing(BUTTON_SPACING);
        let reset_btn = Button::with_icon(grid.row_col(3, 0), theme::ICON_CANCEL)
            .styled(theme::button_cancel())
            .initially_enabled(false)
            .into_child();

        let cancel_btn = Button::with_icon(grid.row_col(3, 0), theme::ICON_CANCEL)
            .styled(theme::button_cancel())
            .initially_enabled(allow_cancel)
            .into_child();

        let confirm_btn = Button::with_icon(grid.row_col(3, 2), theme::ICON_NEXT)
            .styled(theme::button_confirm())
            .initially_enabled(false)
            .into_child();

        // PIN digit buttons.
        let digit_btns = Self::generate_digit_buttons(&grid);

        Self {
            digits,
            allow_cancel,
            major_prompt,
            minor_prompt,
            dots,
            reset_btn,
            cancel_btn,
            confirm_btn,
            digit_btns,
        }
    }

    fn generate_digit_buttons(grid: &Grid) -> [Child<Button<&'static str>>; DIGIT_COUNT] {
        // Generate a random sequence of digits from 0 to 9.
        let mut digits = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"];
        random::shuffle(&mut digits);

        // Assign the digits to buttons on a 5x3 grid, starting from the second row.
        let btn = |i| {
            let area = grid.cell(if i < 9 {
                // The grid has 3 columns, and we skip the first row.
                i
            } else {
                // For the last key (the "0" position) we skip one cell.
                i + 1
            });
            let text = digits[i];
            Child::new(Button::with_text(area, text).styled(theme::button_pin()))
        };
        [
            btn(0),
            btn(1),
            btn(2),
            btn(3),
            btn(4),
            btn(5),
            btn(6),
            btn(7),
            btn(8),
            btn(9),
        ]
    }

    fn pin_modified(&mut self, ctx: &mut EventCtx) {
        let is_full = self.digits.is_full();
        for btn in &mut self.digit_btns {
            btn.mutate(ctx, |ctx, btn| btn.enabled(ctx, !is_full));
        }
        let is_empty = self.digits.is_empty();
        let cancel_enabled = is_empty && self.allow_cancel;
        self.reset_btn
            .mutate(ctx, |ctx, btn| btn.enabled(ctx, !is_empty));
        self.cancel_btn
            .mutate(ctx, |ctx, btn| btn.enabled(ctx, cancel_enabled));
        self.confirm_btn
            .mutate(ctx, |ctx, btn| btn.enabled(ctx, !is_empty));
        let digit_count = self.digits.len();
        self.dots
            .mutate(ctx, |ctx, dots| dots.update(ctx, digit_count));
    }

    pub fn pin(&self) -> &[u8] {
        &self.digits
    }
}

impl<T> Component for PinDialog<T>
where
    T: Deref<Target = [u8]>,
{
    type Msg = PinDialogMsg;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(Clicked) = self.confirm_btn.event(ctx, event) {
            return Some(PinDialogMsg::Confirmed);
        }
        if let Some(Clicked) = self.cancel_btn.event(ctx, event) {
            return Some(PinDialogMsg::Cancelled);
        }
        if let Some(Clicked) = self.reset_btn.event(ctx, event) {
            self.digits.clear();
            self.pin_modified(ctx);
            return None;
        }
        for btn in &mut self.digit_btns {
            if let Some(Clicked) = btn.event(ctx, event) {
                if let ButtonContent::Text(text) = btn.inner().content() {
                    if self.digits.extend_from_slice(text.as_ref()).is_err() {
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
            self.major_prompt.paint();
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

    fn new(area: Rect, digit_count: usize, style: LabelStyle) -> Self {
        Self {
            area,
            style,
            digit_count,
        }
    }

    fn update(&mut self, ctx: &mut EventCtx, digit_count: usize) {
        if digit_count != self.digit_count {
            self.digit_count = digit_count;
            ctx.request_paint();
        }
    }

    /// Clear the area with the background color.
    fn clear(&self) {
        display::rect_fill(self.area, self.style.background_color);
    }

    fn get_size(&self) -> Offset {
        let mut width = Self::DOT * (self.digit_count as i32);
        width += Self::PADDING * (self.digit_count.saturating_sub(1) as i32);
        Offset::new(width, Self::DOT)
    }
}

impl Component for PinDots {
    type Msg = Never;

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        self.clear();

        let mut cursor =
            self.get_size()
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
impl<T> crate::trace::Trace for PinDialog<T>
where
    T: Deref<Target = [u8]>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("PinDialog");
        t.close();
    }
}
