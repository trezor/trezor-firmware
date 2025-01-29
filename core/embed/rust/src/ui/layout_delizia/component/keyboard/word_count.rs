use crate::{
    strutil::TString,
    ui::{
        component::{paginated::SinglePage, Component, Event, EventCtx},
        geometry::{Alignment, Grid, GridCellSpan, Rect},
        shape::Renderer,
    },
};

use heapless::Vec;

use super::super::super::{
    component::button::{Button, ButtonMsg},
    cshape, theme,
};

#[derive(Copy, Clone)]
pub enum SelectWordCountMsg {
    Selected(u32),
    Cancelled,
}

type Cell = (usize, usize);

struct Btn {
    text: TString<'static>,
    msg: SelectWordCountMsg,
    placement: GridCellSpan,
}

impl Btn {
    pub const fn new(content: &'static str, value: u32, cell: Cell) -> Self {
        Self {
            text: TString::Str(content),
            msg: SelectWordCountMsg::Selected(value),
            placement: GridCellSpan {
                from: cell,
                to: (cell.0 + 1, cell.1 + 1),
            },
        }
    }
}

pub struct SelectWordCountLayout {
    choice_buttons: &'static [Btn],
    cancel_button_placement: GridCellSpan,
}

impl SelectWordCountLayout {
    /*
     * 12 | 18
     * -------
     * 20 | 24
     * -------
     *  x | 33
     */
    pub const LAYOUT_ALL: SelectWordCountLayout = SelectWordCountLayout {
        choice_buttons: &[
            Btn::new("12", 12, (0, 0)),
            Btn::new("18", 18, (0, 2)),
            Btn::new("20", 20, (2, 0)),
            Btn::new("24", 24, (2, 2)),
            Btn::new("33", 33, (4, 2)),
        ],
        cancel_button_placement: GridCellSpan {
            from: (4, 0),
            to: (5, 1),
        },
    };

    /*
     * 20 | 33
     * -------
     *    x
     */
    pub const LAYOUT_MULTISHARE: SelectWordCountLayout = SelectWordCountLayout {
        choice_buttons: &[Btn::new("20", 20, (0, 0)), Btn::new("33", 33, (0, 2))],
        cancel_button_placement: GridCellSpan {
            from: (2, 0),
            to: (3, 3),
        },
    };
}

pub struct SelectWordCount {
    keypad_area: Rect,
    layout: SelectWordCountLayout,
    choice_buttons: Vec<Button, 5>,
    cancel_button: Button,
}

impl SelectWordCount {
    pub fn new(layout: SelectWordCountLayout) -> Self {
        let choice_buttons = layout
            .choice_buttons
            .iter()
            .map(|btn| {
                Button::with_text(btn.text)
                    .styled(theme::button_keyboard())
                    .with_text_align(Alignment::Center)
            })
            .collect();

        let cancel_button = Button::with_icon(theme::ICON_CLOSE)
            .styled(theme::button_cancel())
            .with_text_align(Alignment::Center);

        Self {
            keypad_area: Rect::zero(),
            layout,
            choice_buttons,
            cancel_button,
        }
    }
}

impl Component for SelectWordCount {
    type Msg = SelectWordCountMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let n_rows: usize = self.layout.choice_buttons.len() + 1;
        let n_cols: usize = 4;

        let (_, bounds) = bounds.split_bottom(
            n_rows as i16 * theme::BUTTON_HEIGHT + (n_rows as i16 - 1) * theme::BUTTON_SPACING,
        );
        let grid = Grid::new(bounds, n_rows, n_cols).with_spacing(theme::BUTTON_SPACING);
        for (i, button) in self.choice_buttons.iter_mut().enumerate() {
            button.place(grid.cells(self.layout.choice_buttons[i].placement));
        }
        self.cancel_button
            .place(grid.cells(self.layout.cancel_button_placement));
        self.keypad_area = grid.area;
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        for (i, button) in self.choice_buttons.iter_mut().enumerate() {
            if matches!(button.event(ctx, event), Some(ButtonMsg::Clicked)) {
                return Some(self.layout.choice_buttons[i].msg);
            }
        }
        if matches!(
            self.cancel_button.event(ctx, event),
            Some(ButtonMsg::Clicked)
        ) {
            return Some(SelectWordCountMsg::Cancelled);
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        for button in self.choice_buttons.iter() {
            button.render(target);
        }
        self.cancel_button.render(target);

        cshape::KeyboardOverlay::new(self.keypad_area).render(target);
    }
}

impl SinglePage for SelectWordCount {}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for SelectWordCount {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("SelectWordCount");
    }
}
