use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::{Grid, GridCellSpan, Rect},
    model_tt::{
        component::button::{Button, ButtonMsg},
        theme,
    },
};

const NUMBERS: [u32; 5] = [12, 18, 20, 24, 33];
const LABELS: [&str; 5] = ["12", "18", "20", "24", "33"];
const CELLS: [(usize, usize); 5] = [(0, 0), (0, 2), (0, 4), (1, 0), (1, 2)];

pub struct SelectWordCount {
    button: [Button<&'static str>; NUMBERS.len()],
}

pub enum SelectWordCountMsg {
    Selected(u32),
}

impl SelectWordCount {
    pub fn new() -> Self {
        SelectWordCount {
            button: LABELS.map(|t| Button::with_text(t).styled(theme::button_pin())),
        }
    }
}

impl Component for SelectWordCount {
    type Msg = SelectWordCountMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (_, bounds) = bounds.split_bottom(2 * theme::BUTTON_HEIGHT + theme::BUTTON_SPACING);
        let grid = Grid::new(bounds, 2, 6).with_spacing(theme::BUTTON_SPACING);
        for (btn, (x, y)) in self.button.iter_mut().zip(CELLS) {
            btn.place(grid.cells(GridCellSpan {
                from: (x, y),
                to: (x, y + 1),
            }));
        }
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        for (i, btn) in self.button.iter_mut().enumerate() {
            if let Some(ButtonMsg::Clicked) = btn.event(ctx, event) {
                return Some(SelectWordCountMsg::Selected(NUMBERS[i]));
            }
        }
        None
    }

    fn paint(&mut self) {
        for btn in self.button.iter_mut() {
            btn.paint()
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        for btn in self.button.iter() {
            btn.bounds(sink)
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for SelectWordCount {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("SelectWordCount");
    }
}
