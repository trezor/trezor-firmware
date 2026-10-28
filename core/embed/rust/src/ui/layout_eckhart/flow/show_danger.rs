use sys::time::Duration;

use super::super::component::Button;
use super::super::firmware::{
    ActionBar, Header, ShortMenuVec, TextScreen, TextScreenMsg, VerticalMenu, VerticalMenuScreen,
    VerticalMenuScreenMsg,
};
use super::super::theme;
use crate::micropython::{Error, Obj};
use crate::strutil::TString;
use crate::translations::TR;
use crate::ui::component::text::paragraphs::{Paragraph, ParagraphSource, Paragraphs};
use crate::ui::component::ComponentExt;
use crate::ui::flow::base::{Decision, DecisionBuilder as _};
use crate::ui::flow::{FlowController, FlowMsg, SwipeFlow};
use crate::ui::geometry::{Direction, LinearPlacement};
use crate::ui::layout::util::PropsList;

const TIMEOUT: Duration = Duration::from_secs(2);

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
    items: Obj,
    menu_title: Option<TString<'static>>,
    verb_cancel: Option<TString<'static>>,
) -> Result<SwipeFlow, Error> {
    let verb_cancel = verb_cancel.unwrap_or(TR::buttons__cancel_and_exit.into());

    // Contract C3: `None` keeps the plain message. A list of items shows the
    // fields to weigh instead of `value`, and their `Warning` ones are drawn as
    // caution rows.
    let items = if items == Obj::const_none() {
        None
    } else {
        Some(PropsList::new(items)?.with_field_styles(theme::field_styles()))
    };

    match items {
        // Contract C3: the fields carry the message and page through the
        // screen's pager. A description, when there is one, sits under the
        // title rather than above the fields.
        Some(items) => {
            let paragraphs = items
                .into_paragraphs()
                .with_placement(LinearPlacement::vertical());
            let subtitle = if description.is_empty() {
                None
            } else {
                Some(description)
            };
            build_flow(paragraphs, title, subtitle, None, menu_title, verb_cancel)
        }
        // The plain message: a description and the one value to weigh.
        None => {
            let paragraphs = [
                Paragraph::new(&theme::TEXT_REGULAR, description),
                Paragraph::new(&theme::TEXT_MONO_EXTRA_LIGHT, value),
            ]
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical().with_spacing(theme::TEXT_VERTICAL_SPACING));
            build_flow(paragraphs, title, None, Some(1), menu_title, verb_cancel)
        }
    }
}

/// The flow of `show_danger`: the message, the menu to continue anyway or
/// leave, and the cancelled screen on the way out.
fn build_flow<P>(
    paragraphs: Paragraphs<P>,
    title: TString<'static>,
    subtitle: Option<TString<'static>>,
    page_limit: Option<u16>,
    menu_title: Option<TString<'static>>,
    verb_cancel: TString<'static>,
) -> Result<SwipeFlow, Error>
where
    P: ParagraphSource<'static> + 'static,
{
    // Message
    let mut content_message = TextScreen::new(paragraphs).with_header(
        Header::new(title)
            .with_menu_button()
            .with_icon(theme::ICON_INFO, theme::ORANGE)
            .with_text_style(theme::label_title_danger()),
    );
    if let Some(subtitle) = subtitle {
        content_message = content_message.with_subtitle(subtitle);
    }
    if let Some(page_limit) = page_limit {
        content_message = content_message.with_page_limit(page_limit);
    }
    let content_message = content_message
        .with_action_bar(ActionBar::new_single(Button::with_text(verb_cancel)))
        .map(|msg| match msg {
            TextScreenMsg::Menu => Some(FlowMsg::Info),
            TextScreenMsg::Confirmed => Some(FlowMsg::Cancelled),
            _ => None,
        });

    // Menu
    let content_menu = VerticalMenuScreen::new(
        VerticalMenu::<ShortMenuVec>::empty()
            .with_item(Button::new_menu_item(verb_cancel, theme::menu_item_title()))
            .with_item(Button::new_menu_item(
                TR::buttons__continue_anyway.into(),
                theme::menu_item_title_orange(),
            )),
    )
    .with_header(Header::new(menu_title.unwrap_or(TString::empty())).with_close_button())
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
        TIMEOUT,
    ))
    .with_page_limit(1)
    .map(|_| Some(FlowMsg::Confirmed));

    let mut res = SwipeFlow::new(&ShowDanger::Message);
    res.add_page(&ShowDanger::Message, content_message)?
        .add_page(&ShowDanger::Menu, content_menu)?
        .add_page(&ShowDanger::Cancelled, content_cancelled)?;
    Ok(res)
}
