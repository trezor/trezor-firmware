use crate::{
    strutil::TString,
    ui::{
        component::{paginated::SinglePage, Bar, Component, Event, EventCtx, Label, Never},
        geometry::{Grid, Insets, Rect},
        shape::Renderer,
    },
};

use super::super::theme;

pub struct TradeScreen {
    sell_amount: Label<'static>,
    line: Bar,
    buy_amount: Label<'static>,
}

impl TradeScreen {
    pub fn new(sell_amount: TString<'static>, buy_amount: TString<'static>) -> Self {
        Self {
            sell_amount: Label::left_aligned(sell_amount, theme::TEXT_WARNING).top_aligned(),
            line: Bar::new(theme::GREY_EXTRA_DARK, theme::BG, 2),
            buy_amount: Label::left_aligned(buy_amount, theme::TEXT_MAIN_GREEN_LIME)
                .bottom_aligned(),
        }
    }
}

impl SinglePage for TradeScreen {}

impl Component for TradeScreen {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        let grid = Grid::new(bounds, 4, 1);
        self.sell_amount.place(grid.row_col(1, 0));
        self.line.place(
            Rect::new(
                grid.row_col(1, 0).bottom_left(),
                grid.row_col(2, 0).top_right(),
            )
            .outset(Insets::vertical(1)),
        );
        self.buy_amount.place(grid.row_col(2, 0));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.sell_amount.event(ctx, event);
        self.buy_amount.event(ctx, event);
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.sell_amount.render(target);
        self.line.render(target);
        self.buy_amount.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for TradeScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Sell amount");
        t.component("Buy amount");
    }
}
