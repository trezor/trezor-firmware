use crate::{
    strutil::TString,
    ui::{
        component::{
            swipe_detect::SwipeConfig,
            text::paragraphs::{ParagraphSource, Paragraphs},
            Component, Event, EventCtx, FormattedText, PaginateFull,
        },
        flow::Swipable,
        geometry::{Insets, Rect},
        shape::Renderer,
        util::Pager,
    },
};

use super::{action_bar::ActionBarMsg, button::Button, ActionBar, Header, HeaderMsg, Hint};

/// Full-screen component for rendering text.
///
/// T should be either `Paragraphs` or `FormattedText`.
/// The component wraps the full content of the generic page spec:
/// - Header (Optional)
/// - Text
/// - Hint (Optional)
/// - Action bar (Optional)
pub struct TextScreen<T> {
    header: Option<Header>,
    content: T,
    hint: Option<Hint<'static>>,
    action_bar: Option<ActionBar>,
    // TODO: swipe handling
    // TODO: animations
}

pub enum TextScreenMsg {
    Cancelled,
    Confirmed,
    Menu,
}

impl<T> TextScreen<T>
where
    T: AllowedTextContent,
{
    const CONTENT_INSETS: Insets = Insets::sides(24);

    pub fn new(content: T) -> Self {
        Self {
            header: None,
            content,
            hint: None,
            action_bar: None,
        }
    }

    pub fn with_header(mut self, header: Header) -> Self {
        self.header = Some(header);
        self
    }

    pub fn with_hint(mut self, hint: Hint<'static>) -> Self {
        self.hint = Some(hint);
        self
    }

    pub fn with_action_bar(mut self, action_bar: ActionBar) -> Self {
        self.action_bar = Some(action_bar);
        self
    }

    fn update_page(&mut self, page_idx: u16) {
        self.content.change_page(page_idx);
        let pager = self.content.pager();
        self.hint.as_mut().map(|h| h.update(pager));
        self.action_bar.as_mut().map(|ab| ab.update(pager));
    }
}

impl<T> Component for TextScreen<T>
where
    T: AllowedTextContent,
{
    type Msg = TextScreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (header_area, rest) = bounds.split_top(Header::HEADER_HEIGHT);
        let (rest, action_bar_area) = rest.split_bottom(ActionBar::ACTION_BAR_HEIGHT);
        let content_area = if let Some(hint) = &mut self.hint {
            let (rest, hint_area) = rest.split_bottom(hint.height());
            hint.place(hint_area);
            rest
        } else {
            rest
        };
        self.header.place(header_area);
        self.content.place(content_area.inset(Self::CONTENT_INSETS));
        self.action_bar.place(action_bar_area);

        self.update_page(0);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(msg) = self.header.event(ctx, event) {
            match msg {
                HeaderMsg::Cancelled => return Some(TextScreenMsg::Cancelled),
                HeaderMsg::Menu => return Some(TextScreenMsg::Menu),
                _ => {}
            }
        }
        if let Some(msg) = self.action_bar.event(ctx, event) {
            match msg {
                ActionBarMsg::Cancelled => return Some(TextScreenMsg::Cancelled),
                ActionBarMsg::Confirmed => return Some(TextScreenMsg::Confirmed),
                ActionBarMsg::Prev => {
                    self.update_page(self.content.pager().prev());
                    return None;
                }
                ActionBarMsg::Next => {
                    self.update_page(self.content.pager().next());
                    return None;
                }
            }
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.content.render(target);
        self.hint.render(target);
        self.action_bar.render(target);
    }
}

impl<T> Swipable for TextScreen<T>
where
    T: AllowedTextContent,
{
    fn get_pager(&self) -> Pager {
        self.content.pager()
    }
    fn get_swipe_config(&self) -> SwipeConfig {
        SwipeConfig::default()
    }
}

/// A marker trait used to constrain the allowed text content types in a
/// TextScreen.
pub trait AllowedTextContent: Component + PaginateFull {}
impl AllowedTextContent for FormattedText {}
impl<'a, T> AllowedTextContent for Paragraphs<T> where T: ParagraphSource<'a> {}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for TextScreen<T>
where
    T: AllowedTextContent + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("TextComponent");
        self.header.as_ref().map(|header| header.trace(t));
        self.content.trace(t);
        self.hint.as_ref().map(|hint| hint.trace(t));
        self.action_bar.as_ref().map(|ab| ab.trace(t));
    }
}
