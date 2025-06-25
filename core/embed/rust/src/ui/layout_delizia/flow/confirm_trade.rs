use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, Paragraphs},
            CachedJpeg, ComponentExt,
        },
        flow::{
            base::{Decision, DecisionBuilder},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::Direction,
    },
};

use super::super::{
    component::{Frame, PromptScreen, SwipeContent, VerticalMenu},
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

pub fn new_confirm_trade(
    title: TString<'static>,
    subtitle: TString<'static>,
    out_amount: TString<'static>,
    in_amount: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
    let paragraphs = Paragraphs::new([
        Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, out_amount),
        Paragraph::new(&theme::TEXT_MAIN_GREEN_LIGHT, in_amount),
    ]);
    let main_content = Frame::left_aligned(title, SwipeContent::new(paragraphs))
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
