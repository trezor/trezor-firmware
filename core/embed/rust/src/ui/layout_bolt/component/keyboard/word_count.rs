use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::{Grid, GridCellSpan, Rect},
    shape::Renderer,
};

use super::super::{
    super::theme,
    button::{Button, ButtonMsg},
};

use heapless::Vec;

#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum SelectWordCountMsg {
    Selected(u32),
    Cancelled,
}

pub struct SelectWordCount {
    keypad: ValueKeypad,
}

type Label = &'static str;

impl SelectWordCount {
    pub fn new(choices: Vec<u32, 5>, labels: Vec<Label, 5>) -> Self {
        Self {
            keypad: ValueKeypad::new(choices, labels),
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

type Cell = (usize, usize);

struct ValueKeypad {
    buttons: Vec<(Button, Option<u32>, Cell), 6>,
}

impl ValueKeypad {
    /*
     * 0 | 1 | 2
     * ---------
     * x | 3 | 4
     */
    const SIX_CELLS: [Cell; 6] = [(0, 0), (0, 2), (0, 4), (1, 0), (1, 2), (1, 4)];
    const SIX_CELLS_CANCEL_POSITION: usize = 3;

    /*
     * x | 0 | 1
     */
    const THREE_CELLS: [Cell; 3] = [(0, 0), (0, 2), (0, 4)];
    const THREE_CELLS_CANCEL_POSITION: usize = 0;

    fn new(choices: Vec<u32, 5>, labels: Vec<Label, 5>) -> Self {
        let mut buttons = Vec::new();

        let (cells, cancel_position) = match choices.len() {
            5 => (&Self::SIX_CELLS[..], Self::SIX_CELLS_CANCEL_POSITION),
            2 => (&Self::THREE_CELLS[..], Self::THREE_CELLS_CANCEL_POSITION),
            _ => unreachable!(),
        };

        let mut values_vec: Vec<Option<u32>, 6> = choices.iter().copied().map(Some).collect();
        unwrap!(values_vec.insert(cancel_position, None));
        let mut labels_vec: Vec<Label, 6> = labels.iter().copied().collect();
        unwrap!(labels_vec.insert(cancel_position, ""));

        for ((value, label), cell) in values_vec.iter().zip(labels_vec).zip(cells) {
            unwrap!(buttons.push((
                if value.is_none() {
                    Button::with_icon(theme::ICON_CANCEL).styled(theme::button_cancel())
                } else {
                    Button::with_text(label.into()).styled(theme::button_pin())
                },
                *value,
                *cell
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
        for (btn, _, (r, c)) in self.buttons.iter_mut() {
            btn.place(grid.cells(GridCellSpan {
                from: (*r, *c),
                to: (*r, *c + 1),
            }));
        }
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
