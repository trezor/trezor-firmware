use heapless::Vec;

use crate::{
    trezorhal::random,
    ui::{
        component::{
            base::ComponentExt,
            label::{Label, LabelStyle},
            Child, Component, Event, EventCtx, Never,
        },
        display,
        geometry::{Grid, Offset, Point, Rect},
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

pub struct PinKeyboard {
    digits: Vec<u8, MAX_LENGTH>,
    major_prompt: Label<&'static [u8]>,
    minor_prompt: Label<&'static [u8]>,
    dots: Child<PinDots>,
    reset_btn: Child<Button<&'static str>>,
    cancel_btn: Child<Button<&'static str>>,
    confirm_btn: Child<Button<&'static str>>,
    digit_btns: [Child<Button<&'static str>>; DIGIT_COUNT],
}

impl PinKeyboard {
    pub fn new(major_prompt: &'static [u8], minor_prompt: &'static [u8]) -> Self {
        let digits = Vec::new();
        Self {
            major_prompt: Label::centered(major_prompt, theme::label_default()),
            minor_prompt: Label::centered(minor_prompt, theme::label_default()),
            dots: PinDots::new(digits.len(), theme::label_default()).into_child(),
            reset_btn: Button::with_text("Reset")
                .styled(theme::button_clear())
                .into_child(),
            cancel_btn: Button::with_icon(theme::ICON_CANCEL)
                .styled(theme::button_cancel())
                .into_child(),
            confirm_btn: Button::with_icon(theme::ICON_CONFIRM)
                .styled(theme::button_clear())
                .into_child(),
            digit_btns: Self::generate_digit_buttons(),
            digits,
        }
    }

    fn generate_digit_buttons() -> [Child<Button<&'static str>>; DIGIT_COUNT] {
        // Generate a random sequence of digits from 0 to 9.
        let mut digits = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"];
        random::shuffle(&mut digits);
        digits.map(Button::with_text).map(Child::new)
    }

    fn pin_modified(&mut self, ctx: &mut EventCtx) {
        let is_full = self.digits.is_full();
        for btn in &mut self.digit_btns {
            btn.mutate(ctx, |ctx, btn| btn.enable_if(ctx, !is_full));
        }
        let is_empty = self.digits.is_empty();
        self.reset_btn
            .mutate(ctx, |ctx, btn| btn.enable_if(ctx, !is_empty));
        self.cancel_btn
            .mutate(ctx, |ctx, btn| btn.enable_if(ctx, is_empty));
        self.confirm_btn
            .mutate(ctx, |ctx, btn| btn.enable_if(ctx, !is_empty));
        let digit_count = self.digits.len();
        self.dots
            .mutate(ctx, |ctx, dots| dots.update(ctx, digit_count));
    }

    pub fn pin(&self) -> &[u8] {
        &self.digits
    }
}

impl Component for PinKeyboard {
    type Msg = PinKeyboardMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // Prompts and PIN dots display.
        let grid = if self.minor_prompt.text().is_empty() {
            // Make the major prompt bigger if the minor one is empty.
            Grid::new(bounds, 5, 1)
        } else {
            Grid::new(bounds, 6, 1)
        };
        self.major_prompt.place(grid.row_col(0, 0));
        self.minor_prompt.place(grid.row_col(0, 1));
        self.dots.place(grid.row_col(0, 0));

        // Control buttons.
        let grid = Grid::new(bounds, 5, 3);
        self.reset_btn.place(grid.row_col(4, 0));
        self.cancel_btn.place(grid.row_col(4, 0));
        self.confirm_btn.place(grid.row_col(4, 2));

        // Digit buttons.
        for (i, btn) in self.digit_btns.iter_mut().enumerate() {
            // Assign the digits to buttons on a 5x3 grid, starting from the second row.
            let area = grid.cell(if i < 9 {
                // The grid has 3 columns, and we skip the first row.
                i + 3
            } else {
                // For the last key (the "0" position) we skip one cell.
                i + 1 + 3
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
        if self.digits.is_empty() {
            self.cancel_btn.paint();
            self.major_prompt.paint();
            self.minor_prompt.paint();
        } else {
            self.reset_btn.paint();
            self.dots.paint();
        }
        self.confirm_btn.paint();
        for btn in &mut self.digit_btns {
            btn.paint();
        }
    }
}

struct PinDots {
    area: Rect,
    style: LabelStyle,
    digit_count: usize,
}

impl PinDots {
    const DOT: i32 = 10;
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
        // Clear the area with the background color.
        display::rect_fill(self.area, self.style.background_color);

        // Draw a dot for each PIN digit.
        for i in 0..self.digit_count {
            let pos = Point {
                x: self.area.x0 + i as i32 * (Self::DOT + Self::PADDING),
                y: self.area.center().y,
            };
            let size = Offset::new(Self::DOT, Self::DOT);
            display::rect_fill_rounded(
                Rect::from_top_left_and_size(pos, size),
                self.style.text_color,
                self.style.background_color,
                4,
            );
        }
    }
}
