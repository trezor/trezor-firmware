use crate::{
    strutil::TString,
    ui::{
        component::{
            swipe_detect::SwipeConfig,
            text::paragraphs::{Checklist, ParagraphSource, Paragraphs},
            Component, Event, EventCtx, FormattedText, Label, PaginateFull,
        },
        flow::Swipable,
        geometry::{Insets, Rect},
        shape::Renderer,
        util::Pager,
    },
};

use super::{
    action_bar::ActionBarMsg,
    theme::{self, SIDE_INSETS},
    ActionBar, Header, HeaderMsg, Hint,
};

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
    subtitle: Option<Label<'static>>,
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
    const CONTENT_INSETS: Insets = SIDE_INSETS;
    const SUBTITLE_HEIGHT: i16 = 44;

    pub fn new(content: T) -> Self {
        Self {
            header: None,
            subtitle: None,
            content,
            hint: None,
            action_bar: None,
        }
    }

    pub fn with_header(mut self, header: Header) -> Self {
        self.header = Some(header);
        self
    }

    pub fn with_subtitle(mut self, subtitle: TString<'static>) -> Self {
        if !subtitle.is_empty() {
            self.subtitle =
                Some(Label::left_aligned(subtitle, theme::TEXT_MEDIUM_EXTRA_LIGHT).top_aligned());
        }
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
        if let Some(hint) = self.hint.as_mut() {
            hint.update(pager);
        }
        if let Some(ab) = self.action_bar.as_mut() {
            ab.update(pager)
        };
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
        let rest = if let Some(subtitle) = &mut self.subtitle {
            let (subtitle_area, rest) = rest.split_top(Self::SUBTITLE_HEIGHT);
            subtitle.place(subtitle_area.inset(SIDE_INSETS));
            rest
        } else {
            rest
        };

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
        self.subtitle.render(target);
        self.hint.render(target);
        self.action_bar.render(target);
        self.content.render(target);
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
impl<'a, T> AllowedTextContent for Checklist<T> where T: ParagraphSource<'a> {}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for TextScreen<T>
where
    T: AllowedTextContent + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("TextComponent");
        if let Some(header) = self.header.as_ref() {
            header.trace(t);
        }
        if let Some(subtitle) = self.subtitle.as_ref() {
            subtitle.trace(t);
        }
        self.content.trace(t);
        if let Some(hint) = self.hint.as_ref() {
            hint.trace(t);
        }
        if let Some(ab) = self.action_bar.as_ref() {
            ab.trace(t);
        }
    }
}
