use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Label},
        geometry::{Alignment, Insets, Offset, Rect},
        shape::Renderer,
    },
};

use super::super::{
    super::{
        super::constant::SCREEN,
        component::{Button, ButtonMsg},
        theme,
    },
    Header,
};

use heapless::Vec;

pub enum SelectWordCountMsg {
    Cancelled,
    Selected(u32),
}

pub struct SelectWordCountScreen {
    /// Screen header
    header: Header,
    /// Screeen description
    description: Label<'static>,
    /// Value keypad
    keypad: ValueKeypad,
}

impl SelectWordCountScreen {
    const DESCRIPTION_HEIGHT: i16 = 50;
    const KEYPAD_HEIGHT: i16 = 374;

    pub fn new_multi_share(description: TString<'static>) -> Self {
        Self::new(description, ValueKeypad::new_multi_share())
    }

    pub fn new_single_share(description: TString<'static>) -> Self {
        Self::new(description, ValueKeypad::new_single_share())
    }

    fn new(description: TString<'static>, keypad: ValueKeypad) -> Self {
        Self {
            header: Header::new(TString::empty()),
            description: Label::new(description, Alignment::Start, theme::TEXT_MEDIUM)
                .top_aligned(),
            keypad,
        }
    }

    pub fn with_header(mut self, header: Header) -> Self {
        self.header = header;
        self
    }
}

impl Component for SelectWordCountScreen {
    type Msg = SelectWordCountMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (header_area, rest) = bounds.split_top(Header::HEADER_HEIGHT);
        let (description_area, rest) = rest.split_top(Self::DESCRIPTION_HEIGHT);
        let (keypad_area, _) = rest.split_top(Self::KEYPAD_HEIGHT);

        let description_area = description_area.inset(Insets::sides(24));

        self.header.place(header_area);
        self.description.place(description_area);
        self.keypad.place(keypad_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.keypad.event(ctx, event)
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.description.render(target);
        self.keypad.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for SelectWordCountScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("SelectWordCountScreen");
        t.child("description", &self.description);
    }
}

const MAX_KEYS: usize = 8;
pub struct ValueKeypad {
    cancel: Button,
    keys: Vec<Button, MAX_KEYS>,
    numbers: Vec<u32, MAX_KEYS>,
    area: Rect,
    pressed: Option<usize>,
}

impl ValueKeypad {
    const COLS: usize = 3;
    const ROWS: usize = 3;
    const BUTTON_SIZE: Offset = Offset::new(100, 110);
    /// Cancel sits in the last grid cell (bottom-right) for the 8-key layout.
    const CANCEL_BUTTON_INDEX: usize = 8;

    pub fn new_single_share() -> Self {
        const NUMBERS: [u32; 8] = [12, 18, 20, 24, 33, 36, 54, 72];
        const LABELS: [&str; 8] = ["12", "18", "20", "24", "33", "36", "54", "72"];
        Self::new(&LABELS, &NUMBERS)
    }

    pub fn new_multi_share() -> Self {
        const NUMBERS: [u32; 2] = [20, 33];
        const LABELS: [&str; 2] = ["20", "33"];
        Self::new(&LABELS, &NUMBERS)
    }

    fn new(labels: &[&'static str], numbers: &[u32]) -> Self {
        debug_assert_eq!(labels.len(), numbers.len());
        debug_assert!(labels.len() <= MAX_KEYS);

        let keys: Vec<Button, MAX_KEYS> = labels
            .iter()
            .map(|&t| {
                Button::with_text(t.into())
                    .styled(theme::button_keyboard_numeric())
                    .with_text_align(Alignment::Center)
                    .with_radius(12)
            })
            .collect();

        let numbers: Vec<u32, MAX_KEYS> = numbers.iter().copied().collect();

        ValueKeypad {
            cancel: Button::with_icon(theme::ICON_CROSS)
                .styled(theme::button_cancel())
                .with_radius(12),
            keys,
            numbers,
            area: Rect::zero(),
            pressed: None,
        }
    }

    /// Compute button rect for a 3x3 grid cell index (0..=8).
    /// Cells are laid out row-by-row:
    ///   0 | 1 | 2
    ///   3 | 4 | 5
    ///   6 | 7 | 8
    fn get_button_border(&self, idx: usize) -> Rect {
        debug_assert!(idx <= MAX_KEYS);

        let col = (idx % Self::COLS) as i16;
        let row = (idx / Self::COLS) as i16;

        // Equal column / row spacing across the area.
        let col_step = self.area.width() / Self::COLS as i16;
        let row_step = self.area.height() / Self::ROWS as i16;

        // Center the button inside its cell.
        let cx = self.area.x0 + col * col_step + col_step / 2;
        let cy = self.area.y0 + row * row_step + row_step / 2;

        Rect::from_center_and_size(
            crate::ui::geometry::Point::new(cx, cy),
            Self::BUTTON_SIZE,
        )
    }

    fn get_touch_expand(&self, idx: usize) -> Insets {
        debug_assert!(idx <= MAX_KEYS);

        // Equal touch padding to fill the gap between buttons.
        let col_step = self.area.width() / Self::COLS as i16;
        let row_step = self.area.height() / Self::ROWS as i16;
        let h_pad = (col_step - Self::BUTTON_SIZE.x) / 2;
        let v_pad = (row_step - Self::BUTTON_SIZE.y) / 2;

        Insets::new(v_pad, h_pad, v_pad, h_pad)
    }
}

impl Component for ValueKeypad {
    type Msg = SelectWordCountMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // Multi-share recovery (only 2 word counts) uses a centered single
        // column to match the original UX. Single-share recovery has 8 word
        // counts and uses a 3x3 grid (8 keys + cancel in last cell).
        let multi = self.keys.len() < 3;

        self.area = if multi {
            // One narrow column centered
            Rect::from_center_and_size(
                bounds.center(),
                Offset::new(Self::BUTTON_SIZE.x, bounds.height()),
            )
        } else {
            // Full grid area with horizontal padding
            bounds.inset(Insets::sides(20))
        };

        if multi {
            // 3 vertical cells: key0, key1, cancel
            let col_step = self.area.height() / 3;
            for i in 0..self.keys.len() {
                let cy = self.area.y0 + i as i16 * col_step + col_step / 2;
                let rect = Rect::from_center_and_size(
                    crate::ui::geometry::Point::new(self.area.center().x, cy),
                    Self::BUTTON_SIZE,
                );
                self.keys[i].place(rect);
                self.keys[i]
                    .set_expanded_touch_area(Insets::new(8, 0, 8, 0));
            }
            let cancel_cy = self.area.y0 + 2 * col_step + col_step / 2;
            let cancel_rect = Rect::from_center_and_size(
                crate::ui::geometry::Point::new(self.area.center().x, cancel_cy),
                Self::BUTTON_SIZE,
            );
            self.cancel.place(cancel_rect);
            self.cancel
                .set_expanded_touch_area(Insets::new(8, 0, 8, 0));
        } else {
            for i in 0..self.keys.len() {
                let border = self.get_button_border(i);
                let touch_expand = self.get_touch_expand(i);
                self.keys[i].place(border);
                self.keys[i].set_expanded_touch_area(touch_expand);
            }
            self.cancel
                .place(self.get_button_border(Self::CANCEL_BUTTON_INDEX));
            self.cancel
                .set_expanded_touch_area(self.get_touch_expand(Self::CANCEL_BUTTON_INDEX));
        }

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        for (i, btn) in self.keys.iter_mut().enumerate() {
            match btn.event(ctx, event) {
                Some(ButtonMsg::Clicked) => {
                    self.pressed = None;
                    return Some(SelectWordCountMsg::Selected(self.numbers[i]));
                }
                // Detect press of all special buttons for rendering purposes
                Some(ButtonMsg::Pressed) => {
                    self.pressed = Some(i);
                }
                _ => {}
            }
        }

        match self.cancel.event(ctx, event) {
            Some(ButtonMsg::Clicked) => {
                self.pressed = None;
                return Some(SelectWordCountMsg::Cancelled);
            }
            Some(ButtonMsg::Pressed) => {
                // No need to detect press of cancel button bacause of the bottom row placement
                self.pressed = None;
            }
            _ => {}
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        for btn in self.keys.iter() {
            btn.render(target)
        }

        self.cancel.render(target);

        if let Some(idx) = self.pressed {
            self.keys[idx].render(target);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{super::super::constant::SCREEN, *};

    #[test]
    fn test_component_heights_fit_screen() {
        assert!(
            SelectWordCountScreen::DESCRIPTION_HEIGHT
                + SelectWordCountScreen::KEYPAD_HEIGHT
                + Header::HEADER_HEIGHT
                <= SCREEN.height(),
            "Components overflow the screen height",
        );
    }
}
