use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::{Grid, GridCellSpan, Rect},
    model_tt::{
        component::button::{Button, ButtonMsg},
        theme,
    },
    shape::Renderer,
};
use heapless::Vec;

pub enum SelectWordCountMsg {
    Selected(u32),
}

pub struct SelectWordCount {
    keypad: ValueKeypad,
}

impl SelectWordCount {
    const NUMBERS_ALL: [u32; 5] = [12, 18, 20, 24, 33];
    const LABELS_ALL: [&'static str; 5] = ["12", "18", "20", "24", "33"];
    const CELLS_ALL: [(usize, usize); 5] = [(0, 0), (0, 2), (0, 4), (1, 0), (1, 2)];

    const NUMBERS_MULTISHARE: [u32; 2] = [20, 33];
    const LABELS_MULTISHARE: [&'static str; 2] = ["20", "33"];
    const CELLS_MULTISHARE: [(usize, usize); 2] = [(0, 0), (0, 2)];

    pub fn new_all() -> Self {
        Self {
            keypad: ValueKeypad::new(&Self::NUMBERS_ALL, &Self::LABELS_ALL, &Self::CELLS_ALL),
        }
    }

    pub fn new_multishare() -> Self {
        Self {
            keypad: ValueKeypad::new(
                &Self::NUMBERS_MULTISHARE,
                &Self::LABELS_MULTISHARE,
                &Self::CELLS_MULTISHARE,
            ),
        }
    }
}

impl Component for SelectWordCount {
    type Msg = SelectWordCountMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.keypad.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.keypad.event(ctx, event)
    }

    fn paint(&mut self) {
        self.keypad.paint()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.keypad.render(target)
    }
}

type ValueKeyPacked = (Button, u32, (usize, usize)); // (Button, number, cell)

pub struct ValueKeypad {
    buttons: Vec<ValueKeyPacked, 5>,
}

impl ValueKeypad {
    fn new(numbers: &[u32], labels: &[&'static str], cells: &[(usize, usize)]) -> Self {
        let mut buttons = Vec::new();

        for ((&number, &label), &cell) in numbers.iter().zip(labels).zip(cells).take(5) {
            unwrap!(buttons.push((
                Button::with_text(label.into()).styled(theme::button_pin()),
                number,
                cell
            )));
        }

        Self { buttons }
    }
}

impl Component for ValueKeypad {
    type Msg = SelectWordCountMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (_, bounds) = bounds.split_bottom(2 * theme::BUTTON_HEIGHT + theme::BUTTON_SPACING);
        let grid = Grid::new(bounds, 2, 6).with_spacing(theme::BUTTON_SPACING);
        for (btn, _, (x, y)) in self.buttons.iter_mut() {
            btn.place(grid.cells(GridCellSpan {
                from: (*x, *y),
                to: (*x, *y + 1),
            }));
        }
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        for (i, (btn, _, _)) in self.buttons.iter_mut().enumerate() {
            if let Some(ButtonMsg::Clicked) = btn.event(ctx, event) {
                return Some(SelectWordCountMsg::Selected(self.buttons[i].1));
            }
        }
        None
    }

    fn paint(&mut self) {
        for btn in self.buttons.iter_mut() {
            btn.0.paint()
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        for btn in self.buttons.iter() {
            btn.0.render(target)
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for SelectWordCount {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("SelectWordCount");
        t.child("keypad", &self.keypad);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ValueKeypad {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ValueKeypad");
    }
}
