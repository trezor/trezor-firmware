use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::{Alignment, Grid, GridCellSpan, Rect},
    shape::Renderer,
};

use heapless::Vec;

use super::super::super::{
    component::button::{Button, ButtonMsg},
    cshape, theme,
};

pub enum SelectWordCountMsg {
    Selected(u32),
    Cancelled,
}

pub struct SelectWordCount {
    keypad: ValueKeypad,
}

type Value = Option<u32>;
type Label = &'static str;
type Cell = (usize, usize, usize, usize);

impl SelectWordCount {
    const VALUES_ALL: [Value; 6] = [Some(12), Some(18), Some(20), Some(24), None, Some(33)];
    const LABELS_ALL: [Label; 6] = ["12", "18", "20", "24", "", "33"];
    const CELLS_ALL: [Cell; 6] = [
        (0, 0, 1, 1),
        (0, 2, 1, 1),
        (2, 0, 1, 1),
        (2, 2, 1, 1),
        (4, 0, 1, 1),
        (4, 2, 1, 1),
    ];

    const VALUES_MULTISHARE: [Value; 3] = [Some(20), Some(33), None];
    const LABELS_MULTISHARE: [Label; 3] = ["20", "33", ""];
    const CELLS_MULTISHARE: [Cell; 3] = [(0, 0, 1, 1), (0, 2, 1, 1), (2, 0, 3, 1)];

    pub fn new_all() -> Self {
        Self {
            keypad: ValueKeypad::new(&Self::VALUES_ALL, &Self::LABELS_ALL, &Self::CELLS_ALL),
        }
    }

    pub fn new_multishare() -> Self {
        Self {
            keypad: ValueKeypad::new(
                &Self::VALUES_MULTISHARE,
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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.keypad.render(target)
    }
}

struct ValueKeypad {
    buttons: Vec<(Button, Value, Cell), 6>,
    keypad_area: Rect,
}

impl ValueKeypad {
    fn new(values: &[Value], labels: &[Label], cells: &[Cell]) -> Self {
        let mut buttons = Vec::new();

        for ((&value, &label), &cell) in values.iter().zip(labels).zip(cells) {
            unwrap!(buttons.push((
                if value.is_none() {
                    Button::with_icon(theme::ICON_CLOSE).styled(theme::button_cancel())
                } else {
                    Button::with_text(label.into()).styled(theme::button_keyboard())
                }
                .with_text_align(Alignment::Center),
                value,
                cell
            )));
        }

        Self {
            buttons,
            keypad_area: Rect::zero(),
        }
    }
}

impl Component for ValueKeypad {
    type Msg = SelectWordCountMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let n_rows: usize = self.buttons.len();
        let n_cols: usize = 4;

        let (_, bounds) = bounds.split_bottom(
            n_rows as i16 * theme::BUTTON_HEIGHT + (n_rows as i16 - 1) * theme::BUTTON_SPACING,
        );
        let grid = Grid::new(bounds, n_rows, n_cols).with_spacing(theme::BUTTON_SPACING);
        for (btn, _, (r, c, w, h)) in self.buttons.iter_mut() {
            btn.place(grid.cells(GridCellSpan {
                from: (*r, *c),
                to: (*r + *h, *c + *w),
            }));
        }
        self.keypad_area = grid.area;
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        for (btn, value, _) in self.buttons.iter_mut() {
            if matches!(btn.event(ctx, event), Some(ButtonMsg::Clicked)) {
                return Some(match value {
                    Some(number) => SelectWordCountMsg::Selected(*number),
                    None => SelectWordCountMsg::Cancelled,
                });
            }
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        for (btn, _, _) in self.buttons.iter() {
            btn.render(target)
        }

        cshape::KeyboardOverlay::new(self.keypad_area).render(target);
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
