use super::super::component::{Frame, Header, StatusScreen, SwipeContent, VerticalMenu};
use super::super::theme;
use crate::micropython::Error;
use crate::strutil::TString;
use crate::translations::TR;
use crate::ui::component::text::paragraphs::{Paragraph, ParagraphSource};
use crate::ui::flow::base::{Decision, DecisionBuilder as _};
use crate::ui::flow::{FlowController, FlowMsg, SwipeFlow, SwipePage};
use crate::ui::geometry::Direction;
use crate::ui::layout::util::PropsList;

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

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Message, Direction::Up) => Self::Cancelled.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Message, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Choice(1)) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, FlowMsg::Choice(_)) => Self::Cancelled.swipe_up(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Message.swipe_right(),
            (Self::Cancelled, _) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

const EXTRA_PADDING: i16 = 6;

/// The danger page's content: a description, then the fields to weigh, or the
/// plain `value` when there are none.
///
/// The fields carry their own styles and a `Warning` field is drawn as a
/// caution row. A caller that has fields leaves `value` empty.
struct MessageContent {
    description: Paragraph<'static>,
    value: Paragraph<'static>,
    items: Option<PropsList>,
}

impl MessageContent {
    fn has_description(&self) -> bool {
        !self.description.content().is_empty()
    }
}

impl ParagraphSource<'static> for MessageContent {
    fn at(&self, index: usize, offset: usize) -> Paragraph<'static> {
        let has_description = self.has_description();
        if has_description && index == 0 {
            return self.description.skip_prefix(offset);
        }
        let index = index - usize::from(has_description);
        match &self.items {
            Some(items) if index < items.size() => items.at(index, offset),
            _ if index == 0 => self.value.skip_prefix(offset),
            // Out of range: the caller's list ended earlier than `size()`.
            _ => Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, TString::empty()),
        }
    }

    fn size(&self) -> usize {
        let description = usize::from(self.has_description());
        match &self.items {
            Some(items) => description + items.size(),
            // The value is drawn as the second paragraph, even when empty.
            None => description + 1,
        }
    }
}

pub fn new_show_danger(
    title: TString<'static>,
    description: TString<'static>,
    value: TString<'static>,
    items: Option<PropsList>,
    verb_cancel: Option<TString<'static>>,
) -> Result<SwipeFlow, Error> {
    let confirm: TString = TR::buttons__continue_anyway.into();
    let done_title: TString = TR::words__operation_cancelled.into();

    let verb_cancel = verb_cancel.unwrap_or(TR::buttons__cancel_and_exit.into());

    // Message
    let has_items = items.is_some();
    let paragraphs = MessageContent {
        description: Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, description),
        value: Paragraph::new(&theme::TEXT_MAIN_GREY_EXTRA_LIGHT, value)
            .with_top_padding(EXTRA_PADDING),
        items,
    }
    .into_paragraphs();
    // The content pages on its own, one page at a time; the flow's swipe-up
    // keeps its meaning only on the last page, as on every other flow.
    let content_message = Frame::with_header(
        Header::left_aligned(title).with_menu_button().with_danger(),
        SwipeContent::new(SwipePage::vertical(paragraphs)),
    )
    .with_tap_footer(Some(verb_cancel));
    // Fields can run over several pages; the plain message never did.
    let content_message = if has_items {
        content_message.with_vertical_pages()
    } else {
        content_message
    };
    let content_message = content_message.map_to_button_msg();
    // .one_button_request(ButtonRequestCode::Warning, br_name);

    // Menu
    let content_menu = Frame::with_header(
        Header::left_aligned("".into()).with_cancel_button(),
        VerticalMenu::empty()
            .item(theme::ICON_CANCEL, verb_cancel)
            .danger_item(theme::ICON_CHEVRON_RIGHT, confirm),
    )
    .map(super::util::map_to_choice);

    // Cancelled
    let content_cancelled = Frame::with_header(
        Header::left_aligned(TR::words__title_done.into())
            .with_result_icon(theme::ICON_BULLET_CHECKMARK, theme::GREY_DARK),
        StatusScreen::new_neutral_timeout(done_title),
    )
    .with_footer(TR::instructions__continue_in_app.into(), None)
    .map(|_| Some(FlowMsg::Cancelled));

    let mut res = SwipeFlow::new(&ShowDanger::Message);
    res.add_page(&ShowDanger::Message, content_message)?
        .add_page(&ShowDanger::Menu, content_menu)?
        .add_page(&ShowDanger::Cancelled, content_cancelled)?;
    Ok(res)
}
