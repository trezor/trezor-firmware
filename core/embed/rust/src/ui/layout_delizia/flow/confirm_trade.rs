use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            paginated::PaginateFull, swipe_detect::SwipeSettings, Bar, Component, Event, EventCtx,
            Label, Never,
        },
        flow::{
            base::{Decision, DecisionBuilder},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::{Direction, Rect},
        shape::Renderer,
        util::Pager,
    },
};

use super::super::{
    component::{Frame, SwipeContent, VerticalMenu},
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmTrade {
    Main,
    Menu,
}

const CANCEL_INDEX: usize = 0;

impl FlowController for ConfirmTrade {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Main, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Main, Direction::Up) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, Direction::Right) => Self::Main.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Main, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Main, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Main.swipe_right(),
            (Self::Menu, FlowMsg::Choice(CANCEL_INDEX)) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

struct TradeView {
    sell_amount: Label<'static>,
    line: Bar,
    buy_amount: Label<'static>,
}

impl TradeView {
    fn new(sell_amount: TString<'static>, buy_amount: TString<'static>) -> Self {
        Self {
            sell_amount: Label::left_aligned(sell_amount, theme::TEXT_WARNING).top_aligned(),
            line: Bar::new(theme::GREY_DARK, theme::BG, 1),
            buy_amount: Label::left_aligned(buy_amount, theme::TEXT_MAIN_GREEN_LIME)
                .bottom_aligned(),
        }
    }
}

impl PaginateFull for TradeView {
    fn pager(&self) -> Pager {
        Pager::new(1).with_current(0)
    }

    fn change_page(&mut self, _active_page: u16) {
        unimplemented!()
    }
}

impl Component for TradeView {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (top, bottom) = bounds.split_top(bounds.height() / 2);
        let (_top1, top2) = top.split_top(top.height() / 2);
        self.sell_amount.place(top2);
        self.line
            .place(Rect::new(top.bottom_left(), bottom.top_right()).expand(1));
        let (bottom1, _bottom2) = bottom.split_top(bottom.height() / 2);
        self.buy_amount.place(bottom1);
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

pub fn new_confirm_trade(
    title: TString<'static>,
    subtitle: TString<'static>,
    sell_amount: TString<'static>,
    buy_amount: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
    let main_content = Frame::left_aligned(
        title,
        SwipeContent::new(TradeView::new(sell_amount, buy_amount)),
    )
    .with_menu_button()
    .with_swipeup_footer(None)
    .map_to_button_msg();

    let menu_content = Frame::left_aligned(
        TString::empty(),
        VerticalMenu::empty().danger(theme::ICON_CANCEL, TR::buttons__cancel.into()),
    )
    .with_cancel_button()
    .with_swipe(Direction::Right, SwipeSettings::immediate())
    .map(super::util::map_to_choice);

    let mut res = SwipeFlow::new(&ConfirmTrade::Main)?;
    res.add_page(&ConfirmTrade::Main, main_content)?
        .add_page(&ConfirmTrade::Menu, menu_content)?;
    Ok(res)
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for TradeView {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Sell amount");
        t.component("Buy amount");
    }
}
