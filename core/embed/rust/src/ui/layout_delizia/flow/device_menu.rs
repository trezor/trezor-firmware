use crate::{
    error,
    strutil::TString,
    ui::{
        component::{paginated::PaginateFull as _, swipe_detect::SwipeSettings, EventCtx},
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow, SwipePage,
        },
        geometry::Direction,
    },
};

use super::super::component::{Footer, Frame, PagedVerticalMenu, SwipeContent};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum DeviceMenu {
    Menu,
}

impl FlowController for DeviceMenu {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Menu, FlowMsg::Choice(n)) => self.return_msg(FlowMsg::Choice(n)),
            _ => self.return_msg(FlowMsg::Cancelled),
        }
    }
}

const DEMO_OPTIONS: &[&str] = &["Create wallet", "Restore wallet", "Receive BTC", "Send BTC"];

fn footer_update_fn(
    content: &SwipeContent<SwipePage<PagedVerticalMenu<impl Fn(u16) -> TString<'static>>>>,
    ctx: &mut EventCtx,
    footer: &mut Footer,
) {
    let pager = content.inner().inner().pager();
    footer.update_pager(ctx, pager);
}

pub fn new_device_menu() -> Result<SwipeFlow, error::Error> {
    let label_fn =
        move |page_index: u16| -> TString<'static> { DEMO_OPTIONS[page_index as usize].into() };
    let paged_menu = PagedVerticalMenu::new(DEMO_OPTIONS.len(), label_fn);
    let content_menu = Frame::left_aligned(
        "Demo".into(),
        SwipeContent::new(SwipePage::vertical(paged_menu)),
    )
    .with_cancel_button()
    .with_footer_page_hint(
        "More options".into(),
        "".into(),
        "Swipe up".into(),
        "Swipe down".into(),
    )
    .register_footer_update_fn(footer_update_fn)
    .with_swipe(Direction::Down, SwipeSettings::default())
    .with_swipe(Direction::Right, SwipeSettings::immediate())
    .with_vertical_pages()
    .map(|msg| match msg {
        crate::ui::layout_delizia::component::VerticalMenuChoiceMsg::Selected(n) => {
            Some(FlowMsg::Choice(n))
        }
    });
    let mut flow = SwipeFlow::new(&DeviceMenu::Menu)?;
    flow.add_page(&DeviceMenu::Menu, content_menu)?;
    Ok(flow)
}
