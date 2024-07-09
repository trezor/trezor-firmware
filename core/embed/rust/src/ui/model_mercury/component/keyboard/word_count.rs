use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::{Alignment, Grid, GridCellSpan, Rect},
    model_mercury::{
        component::button::{Button, ButtonMsg},
        theme,
    },
    shape::Renderer,
};

const NUMBERS: [u32; 5] = [12, 18, 20, 24, 33];
const LABELS: [&str; 5] = ["12", "18", "20", "24", "33"];
const CELLS: [(usize, usize); 5] = [(0, 0), (0, 2), (1, 0), (1, 2), (2, 1)];

pub struct SelectWordCount {
    button: [Button; NUMBERS.len()],
}

pub enum SelectWordCountMsg {
    Selected(u32),
}

impl SelectWordCount {
    pub fn new() -> Self {
        SelectWordCount {
            button: LABELS.map(|t| {
                Button::with_text(t.into())
                    .styled(theme::button_keyboard())
                    .with_text_align(Alignment::Center)
            }),
        }
    }
}

impl Component for SelectWordCount {
    type Msg = SelectWordCountMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let n_rows: usize = 3;
        let n_cols: usize = 4;

        let (_, bounds) = bounds.split_bottom(
            n_rows as i16 * theme::BUTTON_HEIGHT + (n_rows as i16 - 1) * theme::BUTTON_SPACING,
        );
        let grid = Grid::new(bounds, n_rows, n_cols).with_spacing(theme::BUTTON_SPACING);
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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        for btn in self.button.iter() {
            btn.render(target)
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for SelectWordCount {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("SelectWordCount");
    }
}
