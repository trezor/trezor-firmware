use staticvec::StaticVec;

use crate::trezorhal::display;
use crate::trezorhal::random;
use crate::ui::{
    geometry::{Grid, Point, Rect},
    theme,
};

use super::{
    button::{Button, ButtonContent, ButtonMsg::Clicked},
    component::{Component, Event, Widget},
    label::{Label, LabelStyle},
};

pub enum PinDialogMsg {
    Confirmed,
    Cancelled,
}

const MAX_LENGTH: usize = 9;
const DIGIT_COUNT: usize = 10; // 0..10

pub struct PinDialog {
    widget: Widget,
    pin: StaticVec<u8, MAX_LENGTH>,
    major_prompt: Label<&'static [u8]>,
    minor_prompt: Label<&'static [u8]>,
    dots: PinLabel,
    reset_btn: Button,
    cancel_btn: Button,
    confirm_btn: Button,
    digit_btns: [Button; DIGIT_COUNT],
}

impl PinDialog {
    pub fn new(major_prompt: &'static [u8], minor_prompt: &'static [u8]) -> Self {
        let grid = if minor_prompt.is_empty() {
            // Make the major prompt bigger if the minor one is empty.
            Grid::screen(5, 1)
        } else {
            Grid::screen(6, 1)
        };
        let major_center = grid.row_col(0, 0).midpoint();
        let minor_center = grid.row_col(0, 1).midpoint();
        let major_prompt = Label::centered(major_prompt, theme::label_default(), major_center);
        let minor_prompt = Label::centered(minor_prompt, theme::label_default(), minor_center);
        let dots = PinLabel::new(0, major_center, theme::label_default());

        let grid = Grid::screen(5, 3);
        let reset_content = "Reset".as_bytes();
        let cancel_content = "Cancel".as_bytes();
        let confirm_content = "Confirm".as_bytes();
        let reset_btn = Button::with_text(grid.cell(12), reset_content, theme::button_clear());
        let cancel_btn = Button::with_text(grid.cell(12), cancel_content, theme::button_cancel());
        let confirm_btn = Button::with_text(grid.cell(14), confirm_content, theme::button_clear());

        Self {
            widget: Widget::new(Rect::screen()),
            pin: StaticVec::new(),
            major_prompt,
            minor_prompt,
            dots,
            reset_btn,
            cancel_btn,
            confirm_btn,
            digit_btns: Self::generate_digit_buttons(),
        }
    }

    fn generate_digit_buttons() -> [Button; DIGIT_COUNT] {
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
        let grid = Grid::screen(5, 3);
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
        for btn in &self.digit_btns {
            if self.pin.is_full() {
                btn.disable();
            } else {
                btn.enable();
            }
        }
        if self.pin.is_empty() {
            self.reset_btn.disable();
            self.cancel_btn.disable();
            self.confirm_btn.disable();
        } else {
            self.reset_btn.enable();
            self.cancel_btn.enable();
            self.confirm_btn.enable();
        }
        self.dots.update(self.pin.len());
    }
}

impl Component for PinDialog {
    type Msg = PinDialogMsg;

    fn widget(&mut self) -> &mut Widget {
        &mut self.widget
    }

    fn event(&mut self, event: Event) -> Option<Self::Msg> {
        if let Some(Clicked) = self.confirm_btn.event(event) {
            return Some(PinDialogMsg::Confirmed);
        }
        if let Some(Clicked) = self.cancel_btn.event(event) {
            return Some(PinDialogMsg::Cancelled);
        }
        if let Some(Clicked) = self.reset_btn.event(event) {
            self.pin.clear();
            self.pin_modified();
            return None;
        }
        for btn in &self.digit_btns {
            if let Some(Clicked) = btn.event(event) {
                if let ButtonContent::Text(text) = btn.content() {
                    self.pin.try_extend_from_slice(text);
                    self.pin_modified();
                    return None;
                }
            }
        }
        None
    }

    fn paint(&mut self) {
        self.major_prompt.paint();
        self.minor_prompt.paint();
        if self.pin.is_empty() {
            self.cancel_btn.paint();
        } else {
            self.reset_btn.paint();
        }
        self.confirm_btn.paint();
        for btn in &self.digit_btns {
            btn.paint();
        }
    }
}

struct PinLabel {
    widget: Widget,
    length: usize,
    style: LabelStyle,
}

impl PinLabel {
    const DOT: i32 = 10;
    const PADDING: i32 = 4;

    fn new(length: usize, center: Point, style: LabelStyle) -> Self {
        Self {
            widget: Widget::new(Self::layout(length, center)),
            length,
            style,
        }
    }

    fn layout(length: usize, center: Point) -> Rect {}

    fn update(&mut self, length: usize) {
        if length != self.length {
            self.length = length;
            self.set_area(Self::layout(length, self.center));
        }
    }
}

impl Component for PinLabel {
    type Msg = ();

    fn widget(&mut self) -> &mut Widget {
        &mut self.widget
    }

    fn paint(&mut self) {
        let area = self.area();
        let style = self.style();
        display::bar(
            area.x0,
            area.y0,
            area.width(),
            area.height(),
            style.background_color,
        );
        for i in 0..self.length {
            let pos = Point {
                x: area.x0 + i * (Self::DOT + Self::PADDING),
                y: self.center.y,
            };
            display::bar_radius(
                pos.x,
                pos.y,
                Self::DOT,
                Self::DOT,
                style.text_color,
                style.background_color,
                4,
            );
        }
    }
}
