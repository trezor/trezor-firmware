use crate::{
    error,
    translations::TR,
    ui::{
        button_request::ButtonRequestCode,
        component::{
            text::paragraphs::{Paragraph, ParagraphSource},
            ButtonRequestExt, ComponentExt,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::{Direction, LinearPlacement},
    },
};

use super::super::{
    component::Button,
    firmware::{
        ActionBar, Header, Hint, ShortMenuVec, TextScreen, TextScreenMsg, VerticalMenu,
        VerticalMenuScreen, VerticalMenuScreenMsg,
    },
    theme::{self, gradient::Gradient},
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

    let paragraphs_intro = Paragraph::new(&theme::TEXT_REGULAR, TR::reset__by_continuing)
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical());

    let content_intro = TextScreen::new(paragraphs_intro)
        .with_header(Header::new(title).with_menu_button())
        .with_action_bar(ActionBar::new_single(
            Button::with_text(TR::instructions__hold_to_continue.into())
                .with_long_press(theme::CONFIRM_HOLD_DURATION)
                .styled(theme::button_confirm())
                .with_gradient(Gradient::SignGreen),
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

    let content_menu = VerticalMenuScreen::new(VerticalMenu::<ShortMenuVec>::empty().with_item(
        Button::new_menu_item(TR::buttons__cancel.into(), theme::menu_item_title_orange()),
    ))
    .with_header(Header::new(title).with_close_button())
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
