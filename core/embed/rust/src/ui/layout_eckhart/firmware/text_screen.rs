use crate::{
    strutil::TString,
    ui::{
        component::{
            swipe_detect::SwipeConfig,
            text::{
                layout::LayoutFit,
                paragraphs::{Checklist, ParagraphSource, Paragraphs},
                TextStyle,
            },
            Component, Event, EventCtx, FormattedText, Label, Paginate, TextLayout,
        },
        flow::Swipable,
        geometry::{Insets, Offset, Rect},
        shape::Renderer,
        util::Pager,
    },
};

use super::{
    theme::{self, ScreenBackground, CONTENT_INSETS_NO_HEADER, SIDE_INSETS},
    ActionBar, ActionBarMsg, FidoAccountName, FidoCredential, Header, HeaderMsg, Hint,
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
    page_limit: Option<u16>,
    background: Option<ScreenBackground>,
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
    const SUBTITLE_HEIGHT: i16 = 44;
    const SUBTITLE_DOUBLE_HEIGHT: i16 = 76;
    const SUBTITLE_STYLE: TextStyle = theme::TEXT_MEDIUM_EXTRA_LIGHT;

    pub fn new(content: T) -> Self {
        Self {
            header: None,
            subtitle: None,
            content,
            hint: None,
            action_bar: Some(ActionBar::new_paginate_only()),
            page_limit: None,
            background: None,
        }
    }

    pub fn with_header(mut self, header: Header) -> Self {
        self.header = Some(header);
        self
    }

    pub fn with_subtitle(mut self, subtitle: TString<'static>) -> Self {
        if !subtitle.is_empty() {
            self.subtitle = Some(Label::left_aligned(subtitle, Self::SUBTITLE_STYLE).top_aligned());
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

    pub fn with_page_limit(mut self, page_limit: u16) -> Self {
        self.page_limit = Some(page_limit);
        self
    }

    pub fn with_background(mut self, background: ScreenBackground) -> Self {
        self.background = Some(background);
        self
    }

    fn update_page(&mut self, page_idx: u16) {
        self.content.change_page(page_idx);
        let pager = self.content_pager();

        if let Some(hint) = self.hint.as_mut() {
            hint.update(pager);
        }
        if let Some(ab) = self.action_bar.as_mut() {
            ab.update(pager)
        };
    }

    fn content_pager(&self) -> Pager {
        if let Some(page_limit) = self.page_limit {
            self.content.pager().with_limit(page_limit)
        } else {
            self.content.pager()
        }
    }

    fn place_content_with_hint(&mut self, bounds: Rect) {
        let compute_content_area = |area: Rect, has_header: bool| {
            // Introduce side insets + top padding if the header is not present
            let mut area = area.inset(SIDE_INSETS);
            if !has_header {
                area = area.inset(Insets::top(CONTENT_INSETS_NO_HEADER.top));
            }
            area
        };

        if let Some(hint) = &mut self.hint {
            if hint.is_page_counter() {
                let content_area = compute_content_area(bounds, self.header.is_some());
                self.content.place(content_area);
                // place page counter only if the content doesn't fit on a
                // single page
                if self.content.pager().total() > 1 {
                    let (rest, hint_area) = bounds.split_bottom(hint.height());
                    hint.place(hint_area);
                    let content_area = compute_content_area(rest, self.header.is_some());
                    // re-place content to account for the reduced area
                    self.content.place(content_area);
                } else {
                    self.hint = None;
                }
            } else {
                // always place non-page-counter hints at the bottom
                let (content_area, hint_area) = bounds.split_bottom(hint.height());
                let content_area = compute_content_area(content_area, self.header.is_some());
                hint.place(hint_area);
                self.content.place(content_area);
            }
        } else {
            let content_area = compute_content_area(bounds, self.header.is_some());
            self.content.place(content_area);
        }
        self.update_page(0);
    }
}

impl<T> Component for TextScreen<T>
where
    T: AllowedTextContent,
{
    type Msg = TextScreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let rest = if let Some(header) = &mut self.header {
            let (header_area, rest) = bounds.split_top(Header::HEADER_HEIGHT);
            header.place(header_area);
            rest
        } else {
            bounds
        };

        let rest = if let Some(action_bar) = &mut self.action_bar {
            let (rest, action_bar_area) = rest.split_bottom(ActionBar::ACTION_BAR_HEIGHT);
            action_bar.place(action_bar_area);
            rest
        } else {
            rest
        };

        let rest = if let Some(subtitle) = &mut self.subtitle {
            // Choose appropriate height for the subtitle
            let subtitle_height = if let LayoutFit::OutOfBounds { .. } =
                subtitle.text().map(|text| {
                    TextLayout::new(Self::SUBTITLE_STYLE)
                        .with_bounds(
                            Rect::from_size(Offset::new(bounds.width(), Self::SUBTITLE_HEIGHT))
                                .inset(SIDE_INSETS),
                        )
                        .fit_text(text)
                }) {
                Self::SUBTITLE_DOUBLE_HEIGHT
            } else {
                Self::SUBTITLE_HEIGHT
            };

            let (subtitle_area, rest) = rest.split_top(subtitle_height);
            subtitle.place(subtitle_area.inset(SIDE_INSETS));
            rest
        } else {
            rest
        };

        self.place_content_with_hint(rest);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Update page count of the screen
        ctx.set_page_count(self.content_pager().total());

        self.content.event(ctx, event);
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
                    self.update_page(self.content_pager().prev());
                    return None;
                }
                ActionBarMsg::Next => {
                    self.update_page(self.content_pager().next());
                    return None;
                }
            }
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if let Some(background) = &self.background {
            background.render(target);
        }
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
        self.content_pager()
    }
    fn get_swipe_config(&self) -> SwipeConfig {
        SwipeConfig::default()
    }
}

/// A marker trait used to constrain the allowed text content types in a
/// TextScreen.
pub trait AllowedTextContent: Component + Paginate {}
impl AllowedTextContent for FormattedText {}
impl<'a, T> AllowedTextContent for Paragraphs<T> where T: ParagraphSource<'a> {}
impl<'a, T> AllowedTextContent for Checklist<T> where T: ParagraphSource<'a> {}
impl<F> AllowedTextContent for FidoCredential<F> where F: FidoAccountName {}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for TextScreen<T>
where
    T: AllowedTextContent + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("TextScreen");
        if let Some(header) = self.header.as_ref() {
            t.child("Header", header);
        }
        if let Some(subtitle) = self.subtitle.as_ref() {
            t.child("subtitle", subtitle);
        }
        t.child("Content", &self.content);
        if let Some(hint) = self.hint.as_ref() {
            t.child("Hint", hint);
        }
        if let Some(ab) = self.action_bar.as_ref() {
            t.child("ActionBar", ab);
        }
        if let Some(page_limit) = self.page_limit {
            t.int("page_limit", page_limit as i64);
        }
        t.int("page_count", self.content.pager().total() as i64);
    }
}
