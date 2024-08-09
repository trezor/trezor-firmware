use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::{Alignment, Grid, GridCellSpan, Rect},
    model_mercury::{
        component::{
            button::{Button, ButtonContent, ButtonMsg},
            BinarySelection, BinarySelectionMsg,
        },
        cshape, theme,
    },
    shape::Renderer,
};

pub enum SelectWordCountMsg {
    Selected(u32),
}

// We allow large_enum_variant here because the code is simpler and the larger
// variant (ValueKeypad) predates the smaller one.
#[allow(clippy::large_enum_variant)]
pub enum SelectWordCount {
    All(ValueKeypad),
    Multishare(BinarySelection),
}

impl SelectWordCount {
    pub fn new_all() -> Self {
        Self::All(ValueKeypad::new())
    }

    pub fn new_multishare() -> Self {
        Self::Multishare(BinarySelection::new(
            ButtonContent::Text("20".into()),
            ButtonContent::Text("33".into()),
            theme::button_keyboard(),
            theme::button_keyboard(),
        ))
    }
}

impl Component for SelectWordCount {
    type Msg = SelectWordCountMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        match self {
            SelectWordCount::All(full_selector) => full_selector.place(bounds),
            SelectWordCount::Multishare(bin_selector) => bin_selector.place(bounds),
        }
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match self {
            SelectWordCount::All(full_selector) => full_selector.event(ctx, event),
            SelectWordCount::Multishare(bin_selector) => {
                if let Some(m) = bin_selector.event(ctx, event) {
                    return match m {
                        BinarySelectionMsg::Left => Some(SelectWordCountMsg::Selected(20)),
                        BinarySelectionMsg::Right => Some(SelectWordCountMsg::Selected(33)),
                    };
                }
                None
            }
        }
    }

    fn paint(&mut self) {
        unimplemented!()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        match self {
            SelectWordCount::All(full_selector) => full_selector.render(target),
            SelectWordCount::Multishare(bin_selector) => bin_selector.render(target),
        }
    }
}

pub struct ValueKeypad {
    button: [Button; Self::NUMBERS.len()],
    keypad_area: Rect,
}

impl ValueKeypad {
    const NUMBERS: [u32; 5] = [12, 18, 20, 24, 33];
    const LABELS: [&'static str; 5] = ["12", "18", "20", "24", "33"];
    const CELLS: [(usize, usize); 5] = [(0, 0), (0, 2), (1, 0), (1, 2), (2, 1)];

    fn new() -> Self {
        ValueKeypad {
            button: Self::LABELS.map(|t| {
                Button::with_text(t.into())
                    .styled(theme::button_keyboard())
                    .with_text_align(Alignment::Center)
            }),
            keypad_area: Rect::zero(),
        }
    }
}

impl Component for ValueKeypad {
    type Msg = SelectWordCountMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let n_rows: usize = 3;
        let n_cols: usize = 4;

        let (_, bounds) = bounds.split_bottom(
            n_rows as i16 * theme::BUTTON_HEIGHT + (n_rows as i16 - 1) * theme::BUTTON_SPACING,
        );
        let grid = Grid::new(bounds, n_rows, n_cols).with_spacing(theme::BUTTON_SPACING);
        for (btn, (x, y)) in self.button.iter_mut().zip(Self::CELLS) {
            btn.place(grid.cells(GridCellSpan {
                from: (x, y),
                to: (x, y + 1),
            }));
        }
        self.keypad_area = grid.area;
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        for (i, btn) in self.button.iter_mut().enumerate() {
            if let Some(ButtonMsg::Clicked) = btn.event(ctx, event) {
                return Some(SelectWordCountMsg::Selected(Self::NUMBERS[i]));
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

        cshape::KeyboardOverlay::new(self.keypad_area).render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for SelectWordCount {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("SelectWordCount");
        match self {
            SelectWordCount::All(full_selector) => t.child("all", full_selector),
            SelectWordCount::Multishare(bin_selector) => t.child("multi-share", bin_selector),
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ValueKeypad {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ValueKeypad");
    }
}
