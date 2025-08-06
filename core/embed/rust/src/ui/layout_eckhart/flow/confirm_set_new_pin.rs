use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs},
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
    component::Button,
    firmware::{
        ActionBar, Header, ShortMenuVec, TextScreen, TextScreenMsg, VerticalMenu,
        VerticalMenuScreen, VerticalMenuScreenMsg,
    },
    theme::{self, gradient::Gradient},
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum SetNewPin {
    Intro,
    Menu,
    Cancel,
}

impl FlowController for SetNewPin {
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
            (Self::Menu, FlowMsg::Choice(0)) => Self::Cancel.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Intro.goto(),
            (Self::Cancel, FlowMsg::Cancelled) => Self::Intro.goto(),
            (Self::Cancel, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_set_new_pin(
    title: TString<'static>,
    description: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
    let paragraphs = Paragraphs::new(Paragraph::new(&theme::firmware::TEXT_REGULAR, description))
        .with_placement(LinearPlacement::vertical());
    let content_intro = TextScreen::new(paragraphs)
        .with_header(Header::new(title).with_menu_button())
        .with_action_bar(ActionBar::new_single(Button::with_text(
            TR::buttons__continue.into(),
        )))
        .with_page_limit(1)
        .map(|msg| match msg {
            TextScreenMsg::Menu => Some(FlowMsg::Info),
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            _ => None,
        });

    let content_menu = VerticalMenuScreen::new(VerticalMenu::<ShortMenuVec>::empty().with_item(
        Button::new_menu_item(TR::buttons__cancel.into(), theme::menu_item_title_orange()),
    ))
    .with_header(Header::new(title).with_close_button())
    .map(|msg| match msg {
        VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
        VerticalMenuScreenMsg::Selected(i) => Some(FlowMsg::Choice(i)),
        _ => None,
    });

    let paragraphs_cancel_intro = ParagraphVecShort::from_iter([
        Paragraph::new(&theme::firmware::TEXT_REGULAR, TR::pin__cancel_setup),
        Paragraph::new(&theme::firmware::TEXT_REGULAR, TR::pin__cancel_info),
    ])
    .into_paragraphs()
    .with_placement(LinearPlacement::vertical())
    .with_spacing(24);

    let content_cancel = TextScreen::new(paragraphs_cancel_intro)
        .with_header(
            Header::new(TR::words__important.into())
                .with_text_style(theme::label_title_danger())
                .with_icon(theme::ICON_WARNING, theme::ORANGE),
        )
        .with_action_bar(ActionBar::new_double(
            Button::with_icon(theme::ICON_CHEVRON_LEFT),
            Button::with_text(TR::buttons__cancel.into())
                .styled(theme::button_actionbar_danger())
                .with_gradient(Gradient::Alert),
        ))
        .with_page_limit(1)
        .map(|msg| match msg {
            TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            _ => None,
        });

    let mut res = SwipeFlow::new(&SetNewPin::Intro)?;
    res.add_page(&SetNewPin::Intro, content_intro)?
        .add_page(&SetNewPin::Menu, content_menu)?
        .add_page(&SetNewPin::Cancel, content_cancel)?;
    Ok(res)
}
