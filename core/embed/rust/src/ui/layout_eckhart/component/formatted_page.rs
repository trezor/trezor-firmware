use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, FormattedText, Paginate},
        geometry::Rect,
        shape::Renderer,
    },
};

use super::{action_bar::ActionBarMsg, button::Button, ActionBar, Header, Hint};

/// High-level component for rendering formatted text, possibly paginated. The
/// component wraps the full content of the generic page spec:
/// - Header
/// - Text
/// - Hint (Optional)
/// - Action bar
pub struct FormattedPage {
    header: Header,
    content: FormattedText,
    hint: Option<Hint<'static>>,
    action_bar: ActionBar,
    /// Current index of the paginated `content`
    page_idx: usize,
    /// Max pages of the paginated `content`, computed in `place`
    page_count: usize,
    // TODO: swipe handling
    // TODO: animations
}

pub enum FormattedPageMsg {
    Cancelled,
    Confirmed,
}

impl FormattedPage {
    pub fn new(content: FormattedText) -> Self {
        Self {
            header: Header::new(TString::empty()),
            content,
            hint: None,
            action_bar: ActionBar::new_single(Button::empty()),
            page_idx: 0,
            page_count: 1,
        }
    }

    pub fn with_header(mut self, header: Header) -> Self {
        self.header = header;
        self
    }

    pub fn with_hint(mut self, hint: Hint<'static>) -> Self {
        self.hint = Some(hint);
        self
    }

    pub fn with_action_bar(mut self, action_bar: ActionBar) -> Self {
        self.action_bar = action_bar;
        self
    }

    fn update_page(&mut self) {
        self.content.change_page(self.page_idx);
        if let Some(hint) = &mut self.hint {
            hint.update_page(self.page_idx, self.page_count);
        }
        self.action_bar.update_page(self.page_idx, self.page_count);
    }
}

impl Component for FormattedPage {
    type Msg = FormattedPageMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (header_area, rest) = bounds.split_top(Header::HEADER_HEIGHT);
        let (rest, action_bar_area) = rest.split_bottom(ActionBar::ACTION_BAR_HEIGHT);
        let content_area = if let Some(hint) = &mut self.hint {
            // TODO: hint area based on text
            let (rest, hint_area) = rest.split_bottom(Hint::SINGLE_LINE_HEIGHT);
            hint.place(hint_area);
            rest
        } else {
            rest
        };
        self.header.place(header_area);
        self.content.place(content_area);
        self.action_bar.place(action_bar_area);

        // after computing the layout, update number of pages
        self.page_count = self.content.page_count();
        self.update_page();
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let msg = self.action_bar.event(ctx, event);
        match msg {
            Some(ActionBarMsg::Cancelled) => Some(FormattedPageMsg::Cancelled),
            Some(ActionBarMsg::Confirmed) => Some(FormattedPageMsg::Confirmed),
            Some(ActionBarMsg::Prev) => {
                self.page_idx = (self.page_idx - 1).max(0);
                self.update_page();
                None
            }
            Some(ActionBarMsg::Next) => {
                self.page_idx = (self.page_idx + 1).min(self.page_count - 1);
                self.update_page();
                None
            }
            _ => None,
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.content.render(target);
        if let Some(hint) = &self.hint {
            hint.render(target);
        }
        self.action_bar.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for FormattedPage {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("TextComponent");
        self.header.trace(t);
        self.content.trace(t);
        if let Some(hint) = &self.hint {
            hint.trace(t);
        }
        self.action_bar.trace(t);
    }
}
