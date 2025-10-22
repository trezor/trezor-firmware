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
        geometry::{Offset, Rect},
        shape::Renderer,
        util::Pager,
    },
};

use super::{
    theme::{self, ScreenBackground, CONTENT_INSETS_NO_HEADER, SIDE_INSETS},
    ActionBar, ActionBarMsg, FidoAccountName, FidoCredential, Header, HeaderMsg, Hint,
};

const SUBTITLE_HEIGHT: i16 = 44;
const SUBTITLE_DOUBLE_HEIGHT: i16 = 76;

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
    // runtime visibility flags
    show_action_bar: bool,
    show_page_counter: bool,
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
            show_action_bar: false,
            show_page_counter: false,
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
}

impl<T> Component for TextScreen<T>
where
    T: AllowedTextContent,
{
    type Msg = TextScreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        (self.show_action_bar, self.show_page_counter) = place_textscreen(
            bounds,
            self.header.as_mut(),
            self.subtitle.as_mut(),
            self.hint.as_mut(),
            self.action_bar.as_mut(),
            &mut self.content,
            self.page_limit,
        );

        // Reset to first page and refresh dependent UI
        self.update_page(0);
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

        if self.show_action_bar {
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
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if let Some(background) = &self.background {
            background.render(target);
        }
        self.header.render(target);
        self.subtitle.render(target);

        // Render hint conditionally (page counter only if we decided to show it)
        if let Some(hint) = &self.hint {
            let is_pc = hint.is_page_counter();
            if !is_pc || self.show_page_counter {
                hint.render(target);
            }
        }

        // Render ActionBar only if visible
        if self.show_action_bar {
            if let Some(ab) = &self.action_bar {
                ab.render(target);
            }
        }

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

// Non-generic helpers to reduce monomorphization of TextScreen<T>::place.
// Only dynamic dispatch on content is used here.
trait ContentOps {
    fn place(&mut self, area: Rect);
    fn pager(&self) -> Pager;
}

impl<T> ContentOps for T
where
    T: AllowedTextContent,
{
    fn place(&mut self, area: Rect) {
        Component::place(self, area);
    }
    fn pager(&self) -> Pager {
        Paginate::pager(self)
    }
}

// Lay out the whole screen and decide which optional elements to show.
// Returns (show_action_bar, show_page_counter).
fn place_textscreen(
    bounds: Rect,
    header: Option<&mut Header>,
    subtitle: Option<&mut Label<'static>>,
    hint: Option<&mut Hint<'static>>,
    action_bar: Option<&mut ActionBar>,
    content: &mut dyn ContentOps,
    page_limit: Option<u16>,
) -> (bool, bool) {
    // 1) Header
    let has_header = header.is_some();
    let rest = header.map_or(bounds, |h| {
        let (header_area, rest) = bounds.split_top(Header::HEADER_HEIGHT);
        h.place(header_area);
        rest
    });

    // 2) Subtitle
    let mut content_footer_area = subtitle.map_or(rest, |s| {
        let subtitle_height = if let LayoutFit::OutOfBounds { .. } = s.text().map(|text| {
            TextLayout::new(theme::TEXT_MEDIUM_EXTRA_LIGHT)
                .with_bounds(
                    Rect::from_size(Offset::new(rest.width(), SUBTITLE_HEIGHT)).inset(SIDE_INSETS),
                )
                .fit_text(text)
        }) {
            SUBTITLE_DOUBLE_HEIGHT
        } else {
            SUBTITLE_HEIGHT
        };
        let (subtitle_area, rest) = rest.split_top(subtitle_height);
        s.place(subtitle_area.inset(SIDE_INSETS));
        rest
    });

    // Insets applied to content only
    let mut content_insets = SIDE_INSETS;
    if !has_header {
        content_insets.top += CONTENT_INSETS_NO_HEADER.top;
    }

    // Helper to place content in area and get pager with optional limit
    let mut place_and_pager = |area: Rect| -> Pager {
        let content_area = area.inset(content_insets);
        content.place(content_area);
        let mut pager = content.pager();
        if let Some(limit) = page_limit {
            pager = pager.with_limit(limit);
        }
        pager
    };

    // 4) Compute pagination without AB/hint
    let single_page_without_ab = place_and_pager(content_footer_area).total() <= 1;

    // 5) Decide ActionBar visibility
    let show_action_bar = match action_bar.as_ref() {
        Some(ab) if !ab.is_paginate_only() => true,
        Some(_) => !single_page_without_ab,
        None => false,
    };

    if show_action_bar {
        if let Some(ab) = action_bar {
            let (rest, ab_area) = content_footer_area.split_bottom(ActionBar::ACTION_BAR_HEIGHT);
            ab.place(ab_area);
            content_footer_area = rest;
        }
    }

    // 6) Recompute pagination after AB
    let is_paginated_after_ab = place_and_pager(content_footer_area).total() > 1;

    // 7) Page-counter hint decision
    let hint_is_page_counter = matches!(hint, Some(ref h) if h.is_page_counter());
    let mut show_page_counter = hint_is_page_counter && is_paginated_after_ab;

    // 8) Place hint (if any) and final content
    if let Some(h) = hint {
        let show_hint_now = if hint_is_page_counter {
            show_page_counter
        } else {
            true
        };
        if show_hint_now {
            let (content_top_area, hint_area) = content_footer_area.split_bottom(h.height());
            h.place(hint_area);
            let _ = place_and_pager(content_top_area);
        } else {
            show_page_counter = false;
        }
    }

    (show_action_bar, show_page_counter)
}

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
