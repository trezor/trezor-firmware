use crate::{
    error,
    translations::TR,
    ui::{
        button_request::ButtonRequestCode,
        component::{text::op::OpTextLayout, ButtonRequestExt, ComponentExt, FormattedText},
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::{Alignment, Direction, Offset},
        layout_eckhart::component::Button,
    },
};

use super::super::{
    firmware::{
        ActionBar, Header, HeaderMsg, Hint, TextScreen, TextScreenMsg, VerticalMenu,
        VerticalMenuScreen, VerticalMenuScreenMsg,
    },
    fonts, theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmReset {
    Intro,
    Menu,
}

impl FlowController for ConfirmReset {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Intro, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Intro, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, FlowMsg::Cancelled) => Self::Intro.swipe_right(),
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_confirm_reset(recovery: bool) -> Result<SwipeFlow, error::Error> {
    let (title, br) = if recovery {
        (
            TR::recovery__title_recover.into(),
            ButtonRequestCode::ProtectCall.with_name("recover_device"),
        )
    } else {
        (
            TR::reset__title_create_wallet.into(),
            ButtonRequestCode::ResetDevice.with_name("setup_device"),
        )
    };

    let op = OpTextLayout::new(theme::TEXT_REGULAR)
        .text(TR::reset__by_continuing, fonts::FONT_SATOSHI_REGULAR_38)
        .alignment(Alignment::Start);

    let content_intro = TextScreen::new(FormattedText::new(op))
        .with_header(Header::new(title).with_menu_button())
        .with_action_bar(ActionBar::new_single(
            Button::with_text(TR::instructions__hold_to_continue.into())
                .with_long_press(theme::CONFIRM_HOLD_DURATION)
                .styled(theme::button_confirm()),
        ))
        .with_hint(Hint::new_instruction(
            TR::reset__tos_link,
            Some(theme::ICON_INFO),
        ))
        .map(|msg| match msg {
            TextScreenMsg::Menu => Some(FlowMsg::Info),
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            _ => None,
        })
        .one_button_request(br);

    let content_menu = VerticalMenuScreen::new(
        VerticalMenu::empty().item(
            Button::with_text(TR::buttons__cancel.into())
                .styled(theme::menu_item_title_orange())
                .with_text_align(Alignment::Start)
                .with_content_offset(Offset::x(12)),
        ),
    )
    .with_header(
        Header::new(title)
            .with_right_button(Button::with_icon(theme::ICON_CROSS), HeaderMsg::Cancelled),
    )
    .map(|msg| match msg {
        VerticalMenuScreenMsg::Selected(i) => Some(FlowMsg::Choice(i)),
        VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
        _ => None,
    });

    let mut res = SwipeFlow::new(&ConfirmReset::Intro)?;
    res.add_page(&ConfirmReset::Intro, content_intro)?
        .add_page(&ConfirmReset::Menu, content_menu)?;
    Ok(res)
}
