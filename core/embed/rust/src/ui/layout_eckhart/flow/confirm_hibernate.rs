use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::paragraphs::{Paragraph, Paragraphs},
            ComponentExt as _,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::{Direction, LinearPlacement},
    },
};

use super::super::{
    component::{Button, FuelGauge},
    firmware::{
        ActionBar, Header, Hint, ShortMenuVec, TextScreen, TextScreenMsg, VerticalMenu,
        VerticalMenuScreen, VerticalMenuScreenMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmHibernate {
    Intro,
    Menu,
}

impl FlowController for ConfirmHibernate {
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
            (Self::Intro, FlowMsg::Cancelled) => self.return_msg(FlowMsg::Cancelled),
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Info),
            (Self::Menu, FlowMsg::Cancelled) => Self::Intro.goto(),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_confirm_hibernate(
    description: TString<'static>,
    hint: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
    let paragraphs = Paragraphs::new(Paragraph::new(&theme::firmware::TEXT_REGULAR, description))
        .with_placement(LinearPlacement::vertical());
    let content_intro = TextScreen::new(paragraphs)
        .with_header(
            Header::new(TString::empty())
                .with_menu_button()
                .with_fuel_gauge(Some(FuelGauge::always())),
        )
        .with_hint(Hint::new_instruction(hint, Some(theme::ICON_INFO)))
        .with_action_bar(ActionBar::new_double(
            Button::with_icon(theme::ICON_CROSS),
            Button::with_text(TR::buttons__turn_off.into()),
        ))
        .with_page_limit(1)
        .map(|msg| match msg {
            TextScreenMsg::Menu => Some(FlowMsg::Info),
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
        });

    let content_menu = VerticalMenuScreen::new(VerticalMenu::<ShortMenuVec>::empty().with_item(
        Button::new_menu_item(
            TR::hibernate__start_bootloader.into(),
            theme::menu_item_title(),
        ),
    ))
    .with_header(
        Header::new(TString::empty())
            .with_fuel_gauge(Some(FuelGauge::always()))
            .with_close_button(),
    )
    .map(|msg| match msg {
        VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
        VerticalMenuScreenMsg::Selected(0) => Some(FlowMsg::Choice(0)),
        _ => None,
    });

    let mut res = SwipeFlow::new(&ConfirmHibernate::Intro)?;
    res.add_page(&ConfirmHibernate::Intro, content_intro)?
        .add_page(&ConfirmHibernate::Menu, content_menu)?;
    Ok(res)
}
