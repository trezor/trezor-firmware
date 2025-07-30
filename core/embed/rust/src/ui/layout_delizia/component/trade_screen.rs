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
            sell_amount: Label::left_aligned(sell_amount, theme::TEXT_WARNING).bottom_aligned(),
            line: Bar::new(theme::GREY_EXTRA_DARK, theme::BG, 2),
            buy_amount: Label::left_aligned(buy_amount, theme::TEXT_MAIN_GREEN_LIME).top_aligned(),
        }
    }
}

impl SinglePage for TradeScreen {}

impl Component for TradeScreen {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (top, bottom) = bounds.split_top(bounds.height() / 2);
        let (sell_bounds, _) = top.split_bottom(self.sell_amount.font().text_height());
        self.sell_amount.place(sell_bounds);
        self.line
            .place(Rect::new(top.bottom_left(), bottom.top_right()).outset(Insets::vertical(1)));
        let (_, buy_bounds) = bottom.split_top(self.buy_amount.font().text_height());
        self.buy_amount.place(buy_bounds);
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
