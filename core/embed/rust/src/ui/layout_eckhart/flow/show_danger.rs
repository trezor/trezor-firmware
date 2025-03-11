use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::paragraphs::{Paragraph, ParagraphSource},
            ComponentExt,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::{Alignment, Direction, LinearPlacement, Offset},
    },
};

use super::super::{
    component::Button,
    firmware::{
        ActionBar, Header, HeaderMsg, TextScreen, TextScreenMsg, VerticalMenu, VerticalMenuScreen,
        VerticalMenuScreenMsg,
    },
    theme,
};

const TIMEOUT_MS: u32 = 2000;

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ShowDanger {
    Message,
    Menu,
    Cancelled,
}

impl FlowController for ShowDanger {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Message, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Message, FlowMsg::Cancelled) => Self::Cancelled.goto(),
            (Self::Menu, FlowMsg::Choice(1)) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, FlowMsg::Choice(_)) => Self::Cancelled.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Message.goto(),
            (Self::Cancelled, _) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_show_danger(
    title: TString<'static>,
    description: TString<'static>,
    value: TString<'static>,
    menu_title: Option<TString<'static>>,
    verb_cancel: Option<TString<'static>>,
) -> Result<SwipeFlow, error::Error> {
    let verb_cancel = verb_cancel.unwrap_or(TR::words__cancel_and_exit.into());

    // Message
    let paragraphs = [
        Paragraph::new(&theme::TEXT_REGULAR, description),
        Paragraph::new(&theme::TEXT_MONO_EXTRA_LIGHT, value),
    ]
    .into_paragraphs()
    .with_placement(LinearPlacement::vertical().with_spacing(35));

    let content_message = TextScreen::new(paragraphs)
        .with_header(
            Header::new(title)
                .with_menu_button()
                .with_icon(theme::ICON_INFO, theme::ORANGE)
                .with_text_style(theme::label_title_danger()),
        )
        .with_action_bar(ActionBar::new_single(Button::with_text(verb_cancel)))
        .map(|msg| match msg {
            TextScreenMsg::Menu => Some(FlowMsg::Info),
            TextScreenMsg::Confirmed => Some(FlowMsg::Cancelled),
            _ => None,
        });

    // Menu
    let content_menu = VerticalMenuScreen::new(
        VerticalMenu::empty()
            .with_separators()
            .item(
                Button::with_text(verb_cancel)
                    .styled(theme::menu_item_title())
                    .with_text_align(Alignment::Start)
                    .with_content_offset(Offset::x(12)),
            )
            .item(
                Button::with_text(TR::words__continue_anyway.into())
                    .styled(theme::menu_item_title_orange())
                    .with_text_align(Alignment::Start)
                    .with_content_offset(Offset::x(12)),
            ),
    )
    .with_header(
        Header::new(menu_title.unwrap_or("".into()))
            .with_right_button(Button::with_icon(theme::ICON_CROSS), HeaderMsg::Cancelled),
    )
    .map(|msg| match msg {
        VerticalMenuScreenMsg::Selected(i) => Some(FlowMsg::Choice(i)),
        VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
        _ => None,
    });

    // Cancelled
    let content_cancelled = TextScreen::new(
        Paragraph::new(&theme::TEXT_REGULAR, TR::words__operation_cancelled)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical()),
    )
    .with_header(Header::new(TR::words__title_done.into()).with_icon(theme::ICON_DONE, theme::GREY))
    .with_action_bar(ActionBar::new_timeout(
        Button::with_text(TR::instructions__continue_in_app.into()),
        TIMEOUT_MS,
    ))
    .map(|_| Some(FlowMsg::Confirmed));

    let mut res = SwipeFlow::new(&ShowDanger::Message)?;
    res.add_page(&ShowDanger::Message, content_message)?
        .add_page(&ShowDanger::Menu, content_menu)?
        .add_page(&ShowDanger::Cancelled, content_cancelled)?;
    Ok(res)
}
