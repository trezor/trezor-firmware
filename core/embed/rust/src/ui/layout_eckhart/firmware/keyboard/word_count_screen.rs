use heapless::Vec;

use super::super::super::super::constant::SCREEN;
use super::super::super::component::{Button, ButtonMsg};
use super::super::super::theme;
use super::super::Header;
use crate::strutil::TString;
use crate::ui::component::{Component, Event, EventCtx, Label};
use crate::ui::geometry::{Alignment, Insets, Offset, Rect};
use crate::ui::shape::Renderer;

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
    const DESCRIPTION_HEIGHT: i16 = 71;
    const KEYPAD_HEIGHT: i16 = 334;

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

const MAX_KEYS: usize = 7;
pub struct ValueKeypad {
    cancel: Button,
    keys: Vec<Button, MAX_KEYS>,
    numbers: Vec<u32, MAX_KEYS>,
    /// Number of rows of the keypad grid.
    rows: usize,
    /// Size of a single key.
    button_size: Offset,
    /// Grid cell of the cancel button, in the bottom-left corner.
    cancel_cell: usize,
    area: Rect,
    pressed: Option<usize>,
}

impl ValueKeypad {
    /// Grid used when the values do not fit into a single column.
    const ROWS_TWO_COLUMNS: usize = 4;
    const BUTTON_SIZE_TWO_COLUMNS: Offset = Offset::new(138, 76);
    /// Grid used when all the values fit into a single column.
    const ROWS_ONE_COLUMN: usize = 3;
    const BUTTON_SIZE_ONE_COLUMN: Offset = Offset::new(138, 130);
    /// Number of values from which the two-column grid is used.
    const TWO_COLUMNS_THRESHOLD: usize = 3;

    pub fn new_single_share() -> Self {
        // Values are column-major, with the cancel button in the bottom-left cell.
        const NUMBERS: [u32; 7] = [12, 18, 21, 15, 20, 24, 33];
        const LABELS: [&str; 7] = ["12", "18", "21", "15", "20", "24", "33"];
        Self::new(&LABELS, &NUMBERS)
    }

    pub fn new_multi_share() -> Self {
        const NUMBERS: [u32; 2] = [20, 33];
        const LABELS: [&str; 2] = ["20", "33"];
        Self::new(&LABELS, &NUMBERS)
    }

    /// Convert key index to grid cell index.
    fn key_2_grid_cell(&self, key: usize) -> usize {
        // Make sure the key is within bounds.
        debug_assert!(key < MAX_KEYS);
        // Keys after the bottom-left cancel button continue in the right column.
        if key < self.cancel_cell {
            key
        } else {
            key + 1
        }
    }

    fn new(labels: &[&'static str], numbers: &[u32]) -> Self {
        debug_assert_eq!(labels.len(), numbers.len());
        debug_assert!(labels.len() <= MAX_KEYS);

        // A short list of values is laid out in a single column of taller keys.
        let two_columns = labels.len() >= Self::TWO_COLUMNS_THRESHOLD;
        let rows = if two_columns {
            Self::ROWS_TWO_COLUMNS
        } else {
            Self::ROWS_ONE_COLUMN
        };
        let button_size = if two_columns {
            Self::BUTTON_SIZE_TWO_COLUMNS
        } else {
            Self::BUTTON_SIZE_ONE_COLUMN
        };

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
            rows,
            button_size,
            cancel_cell: rows - 1,
            area: Rect::zero(),
            pressed: None,
        }
    }

    fn vertical_spacing(&self) -> i16 {
        (self.area.height() - self.button_size.y * self.rows as i16) / (self.rows as i16 - 1)
    }

    fn get_button_border(&self, idx: usize) -> Rect {
        // Make sure the key is within bounds.
        debug_assert!(idx <= MAX_KEYS);
        let column = idx / self.rows;
        let row = idx % self.rows;
        let horizontal_spacing = self.area.width() - 2 * self.button_size.x;
        let vertical_spacing = self.vertical_spacing();
        let offset = Offset::new(
            column as i16 * (self.button_size.x + horizontal_spacing),
            row as i16 * (self.button_size.y + vertical_spacing),
        );
        Rect::from_top_left_and_size(self.area.top_left().ofs(offset), self.button_size)
    }

    fn get_touch_expand(&self, idx: usize) -> Insets {
        debug_assert!(idx <= MAX_KEYS); // Ensure the index is within bounds.

        let vertical_spacing = self.vertical_spacing();

        if idx.is_multiple_of(self.rows) {
            Insets::bottom(vertical_spacing / 2)
        } else if idx % self.rows == self.rows - 1 {
            Insets::top(vertical_spacing / 2)
        } else {
            Insets::new(vertical_spacing / 2, 0, vertical_spacing / 2, 0)
        }
    }
}

impl Component for ValueKeypad {
    type Msg = SelectWordCountMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = if self.keys.len() < Self::TWO_COLUMNS_THRESHOLD {
            // One column
            Rect::from_center_and_size(
                bounds.center(),
                Offset::new(self.button_size.x, bounds.height()),
            )
        } else {
            // Two columns
            bounds.inset(Insets::sides(42))
        };

        for i in 0..self.keys.len() {
            let cell = self.key_2_grid_cell(i);
            let border = self.get_button_border(cell);
            let touch_expand = self.get_touch_expand(cell);
            self.keys[i].place(border);
            self.keys[i].set_expanded_touch_area(touch_expand);
        }

        let cancel_border = self.get_button_border(self.cancel_cell);
        let cancel_touch_expand = self.get_touch_expand(self.cancel_cell);
        self.cancel.place(cancel_border);
        self.cancel.set_expanded_touch_area(cancel_touch_expand);

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
    use super::super::super::constant::SCREEN;
    use super::*;

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
