use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Label},
        geometry::{Alignment, Insets, Offset, Rect},
        shape::Renderer,
    },
};

use super::super::{
    super::{super::constant::SCREEN, theme},
    Button, ButtonMsg, Header,
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

const MAX_KEYS: usize = 5;
pub struct ValueKeypad {
    cancel: Button,
    keys: Vec<Button, MAX_KEYS>,
    numbers: Vec<u32, MAX_KEYS>,
    area: Rect,
    pressed: Option<usize>,
}

impl ValueKeypad {
    const ROWS: usize = 3;
    const BUTTON_SIZE: Offset = Offset::new(138, 130);
    const CANCEL_BUTTON_INDEX: usize = 2;

    pub fn new_single_share() -> Self {
        const NUMBERS: [u32; 5] = [12, 24, 18, 20, 33];
        const LABELS: [&'static str; 5] = ["12", "24", "18", "20", "33"];
        Self::new(&LABELS, &NUMBERS)
    }

    pub fn new_multi_share() -> Self {
        const NUMBERS: [u32; 2] = [20, 33];
        const LABELS: [&'static str; 2] = ["20", "33"];
        Self::new(&LABELS, &NUMBERS)
    }

    /// Convert key index to grid cell index.
    fn key_2_grid_cell(key: usize) -> usize {
        // Make sure the key is within bounds.
        debug_assert!(key < MAX_KEYS);
        // Key with index 2 must be mapped after the cancel button.
        if key < Self::CANCEL_BUTTON_INDEX {
            key
        } else {
            key + 1
        }
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

    fn get_button_border(&self, idx: usize) -> Rect {
        // Make sure the key is within bounds.
        debug_assert!(idx < MAX_KEYS);
        match idx {
            0 => Rect::from_top_left_and_size(self.area.top_left(), Self::BUTTON_SIZE),
            1 => Rect::from_center_and_size(
                self.area
                    .left_center()
                    .ofs(Offset::x(Self::BUTTON_SIZE.x / 2)),
                Self::BUTTON_SIZE,
            ),
            2 => Rect::from_bottom_left_and_size(self.area.bottom_left(), Self::BUTTON_SIZE),
            3 => Rect::from_top_right_and_size(self.area.top_right(), Self::BUTTON_SIZE),
            4 => Rect::from_center_and_size(
                self.area
                    .right_center()
                    .ofs(Offset::x(-Self::BUTTON_SIZE.x / 2)),
                Self::BUTTON_SIZE,
            ),
            5 => Rect::from_bottom_right_and_size(self.area.bottom_right(), Self::BUTTON_SIZE),
            _ => Rect::zero(), // Default case for out-of-range indices.
        }
    }

    fn get_touch_expand(&self, idx: usize) -> Insets {
        debug_assert!(idx < MAX_KEYS); // Ensure the index is within bounds.

        let vertical_spacing = (self.area.height() - Self::BUTTON_SIZE.y * Self::ROWS as i16)
            / (Self::ROWS as i16 - 1);

        if idx % Self::ROWS == 0 {
            Insets::bottom(vertical_spacing / 2)
        } else if idx % Self::ROWS == Self::ROWS - 1 {
            Insets::top(vertical_spacing / 2)
        } else {
            Insets::new(vertical_spacing / 2, 0, vertical_spacing / 2, 0)
        }
    }
}

impl Component for ValueKeypad {
    type Msg = SelectWordCountMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = if self.keys.len() < 3 {
            // One column
            Rect::from_center_and_size(
                bounds.center(),
                Offset::new(Self::BUTTON_SIZE.x, bounds.height()),
            )
        } else {
            // Two columns
            bounds.inset(Insets::sides(42))
        };

        for i in 0..self.keys.len() {
            let cell = Self::key_2_grid_cell(i);
            let border = self.get_button_border(cell);
            let touch_expand = self.get_touch_expand(cell);
            self.keys[i].place(border);
            self.keys[i].set_expanded_touch_area(touch_expand);
        }

        self.cancel
            .place(self.get_button_border(Self::CANCEL_BUTTON_INDEX));
        self.cancel
            .set_expanded_touch_area(self.get_touch_expand(Self::CANCEL_BUTTON_INDEX));

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
