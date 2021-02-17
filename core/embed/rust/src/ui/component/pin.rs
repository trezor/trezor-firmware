use staticvec::StaticVec;

use crate::trezorhal::random;
use crate::ui::{
    display,
    math::{Grid, Offset, Point, Rect},
    theme,
};

use super::{
    button::{Button, ButtonContent, ButtonMsg::Clicked},
    component::{Component, Event, EventCtx, Widget},
    label::{Label, LabelStyle},
};

pub enum PinDialogMsg {
    Confirmed,
    Cancelled,
}

pub struct PinDialog {
    widget: Widget,
    digits: StaticVec<u8, MAX_LENGTH>,
    major_prompt: Label<&'static [u8]>,
    minor_prompt: Label<&'static [u8]>,
    dots: PinDots,
    reset_btn: Button,
    cancel_btn: Button,
    confirm_btn: Button,
    digit_btns: [Button; DIGIT_COUNT],
}

const MAX_LENGTH: usize = 9;
const DIGIT_COUNT: usize = 10; // 0..10

impl PinDialog {
    pub fn new(area: Rect, major_prompt: &'static [u8], minor_prompt: &'static [u8]) -> Self {
        let digits = StaticVec::new();

        let grid = if minor_prompt.is_empty() {
            // Make the major prompt bigger if the minor one is empty.
            Grid::new(area, 5, 1)
        } else {
            Grid::new(area, 6, 1)
        };
        let major_center = grid.row_col(0, 0).midpoint();
        let minor_center = grid.row_col(0, 1).midpoint();
        let major_prompt = Label::centered(major_center, major_prompt, theme::label_default());
        let minor_prompt = Label::centered(minor_center, minor_prompt, theme::label_default());
        let dots = PinDots::new(major_center, digits.len(), theme::label_default());

        let grid = Grid::new(area, 5, 3);
        let reset_content = "Reset".as_bytes();
        let cancel_content = "Cancel".as_bytes();
        let confirm_content = "Confirm".as_bytes();
        let reset_btn = Button::with_text(grid.cell(12), reset_content, theme::button_clear());
        let cancel_btn = Button::with_text(grid.cell(12), cancel_content, theme::button_cancel());
        let confirm_btn = Button::with_text(grid.cell(14), confirm_content, theme::button_clear());

        Self {
            widget: Widget::new(area),
            digits,
            major_prompt,
            minor_prompt,
            dots,
            reset_btn,
            cancel_btn,
            confirm_btn,
            digit_btns: Self::generate_digit_buttons(&grid),
        }
    }

    fn generate_digit_buttons(grid: &Grid) -> [Button; DIGIT_COUNT] {
        // Generate a random sequence of digits from 0 to 9.
        let mut digits = [
            "0".as_bytes(),
            "1".as_bytes(),
            "2".as_bytes(),
            "3".as_bytes(),
            "4".as_bytes(),
            "5".as_bytes(),
            "6".as_bytes(),
            "7".as_bytes(),
            "8".as_bytes(),
            "9".as_bytes(),
        ];
        random::shuffle(&mut digits);

        // Assign the digits to buttons on a 5x3 grid, starting from the second row.
        let btn = |i| {
            let area = grid.cell(if i < 9 {
                // The grid has 3 columns, and we skip the first row.
                i + 3
            } else {
                // For the last key (the "0" position) we skip one cell.
                i + 1 + 3
            });
            Button::with_text(area, digits[i], theme::button_default())
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

    fn pin_modified(&mut self) {
        for btn in &mut self.digit_btns {
            if self.digits.is_full() {
                btn.disable();
            } else {
                btn.enable();
            }
        }
        if self.digits.is_empty() {
            self.reset_btn.disable();
            self.cancel_btn.disable();
            self.confirm_btn.disable();
        } else {
            self.reset_btn.enable();
            self.cancel_btn.enable();
            self.confirm_btn.enable();
        }
        self.dots.update(self.digits.len());
    }

    pub fn pin(&self) -> &[u8] {
        &self.digits
    }
}

impl Component for PinDialog {
    type Msg = PinDialogMsg;

    fn widget(&mut self) -> &mut Widget {
        &mut self.widget
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(Clicked) = self.confirm_btn.event(ctx, event) {
            return Some(PinDialogMsg::Confirmed);
        }
        if let Some(Clicked) = self.cancel_btn.event(ctx, event) {
            return Some(PinDialogMsg::Cancelled);
        }
        if let Some(Clicked) = self.reset_btn.event(ctx, event) {
            self.digits.clear();
            self.pin_modified();
            return None;
        }
        for btn in &mut self.digit_btns {
            if let Some(Clicked) = btn.event(ctx, event) {
                if let ButtonContent::Text(text) = btn.content() {
                    if self.digits.try_extend_from_slice(text).is_err() {
                        // `self.pin` is full and wasn't able to accept all of
                        // `text`. Should not happen.
                    }
                    self.pin_modified();
                    return None;
                }
            }
        }
        None
    }

    fn paint(&mut self) {
        self.major_prompt.paint_if_requested();
        self.minor_prompt.paint_if_requested();
        if self.digits.is_empty() {
            self.cancel_btn.paint_if_requested();
        } else {
            self.reset_btn.paint_if_requested();
        }
        self.confirm_btn.paint_if_requested();
        for btn in &mut self.digit_btns {
            btn.paint_if_requested();
        }
    }
}

struct PinDots {
    widget: Widget,
    style: LabelStyle,
    digit_count: usize,
}

impl PinDots {
    const DOT: i32 = 10;
    const PADDING: i32 = 4;

    fn new(center: Point, digit_count: usize, style: LabelStyle) -> Self {
        Self {
            widget: Widget::new(Self::layout(center, digit_count)),
            style,
            digit_count,
        }
    }

    fn layout(center: Point, digit_count: usize) -> Rect {
        todo!()
    }

    fn update(&mut self, digit_count: usize) {
        if digit_count != self.digit_count {
            self.digit_count = digit_count;
            let area = Self::layout(self.area().midpoint(), digit_count);
            self.set_area(area);
            self.request_paint();
        }
    }
}

impl Component for PinDots {
    type Msg = !;

    fn widget(&mut self) -> &mut Widget {
        &mut self.widget
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        let area = self.area();

        // Clear the area with the background color.
        display::rect(area, self.style.background_color);

        // Draw a dot for each PIN digit.
        for i in 0..self.digit_count {
            let pos = Point {
                x: area.x0 + i as i32 * (Self::DOT + Self::PADDING),
                y: area.midpoint().y,
            };
            let size = Offset::new(Self::DOT, Self::DOT);
            display::rounded_rect(
                Rect::with_size(pos, size),
                self.style.text_color,
                self.style.background_color,
                4,
            );
        }
    }
}
