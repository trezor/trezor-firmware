use crate::{
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeConfig,
            text::paragraphs::{Paragraph, ParagraphSource, Paragraphs},
            Component, Event, EventCtx, Paginate,
        },
        flow::Swipable,
        geometry::{LinearPlacement, Rect},
        shape::Renderer,
        util::Pager,
    },
};

use super::{constant::SCREEN, theme, ActionBar, ActionBarMsg, Header};

pub enum UpdatableInfoScreenMsg {
    Close,
}

pub struct UpdatableInfoScreen<F>
where
    F: Fn() -> TString<'static>,
{
    header: Header,
    info_func: F,
    paragraph: Paragraphs<Paragraph<'static>>,
    action_bar: ActionBar,
}

impl<F> UpdatableInfoScreen<F>
where
    F: Fn() -> TString<'static>,
{
    pub fn new(info_func: F) -> Self {
        let paragraph = Paragraph::new(&theme::TEXT_REGULAR, TString::empty())
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical());
        Self {
            header: Header::new(TR::buttons__more_info.into()).with_close_button(),
            info_func,
            paragraph,
            action_bar: ActionBar::new_paginate_only(),
        }
    }

    pub fn with_header(mut self, header: Header) -> Self {
        self.header = header;
        self
    }

    fn update_text(&mut self, ctx: &mut EventCtx) {
        let text = (self.info_func)();
        self.paragraph.update(text);

        self.update_page(0);
        ctx.request_paint();
    }

    fn update_page(&mut self, page_idx: u16) {
        self.paragraph.change_page(page_idx);
        self.action_bar.update(self.paragraph.pager());
    }
}

impl<F> Component for UpdatableInfoScreen<F>
where
    F: Fn() -> TString<'static>,
{
    type Msg = UpdatableInfoScreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (header_area, rest) = bounds.split_top(Header::HEADER_HEIGHT);
        let (info_area, action_bar_area) = rest.split_bottom(ActionBar::ACTION_BAR_HEIGHT);

        self.header.place(header_area);
        self.paragraph.place(info_area.inset(theme::SIDE_INSETS));
        self.action_bar.place(action_bar_area);

        self.update_page(0);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Update page count of the screen
        ctx.set_page_count(self.paragraph.pager().total());

        if let Event::Attach(_) = event {
            self.update_text(ctx);
        }

        self.paragraph.event(ctx, event);

        if self.header.event(ctx, event).is_some() {
            return Some(UpdatableInfoScreenMsg::Close);
        }

        if let Some(msg) = self.action_bar.event(ctx, event) {
            match msg {
                ActionBarMsg::Prev => {
                    self.update_page(self.paragraph.pager().prev());
                    return None;
                }
                ActionBarMsg::Next => {
                    self.update_page(self.paragraph.pager().next());
                    return None;
                }
                _ => {}
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.paragraph.render(target);
        self.action_bar.render(target);
    }
}

impl<F: Fn() -> TString<'static>> Swipable for UpdatableInfoScreen<F> {
    fn get_pager(&self) -> Pager {
        Pager::single_page()
    }
    fn get_swipe_config(&self) -> SwipeConfig {
        SwipeConfig::default()
    }
}

trait UpdatableTextContent: Component + Paginate {}
impl<'a, T> UpdatableTextContent for Paragraphs<T> where T: ParagraphSource<'a> {}

#[cfg(feature = "ui_debug")]
impl<F> crate::trace::Trace for UpdatableInfoScreen<F>
where
    F: Fn() -> TString<'static>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("UpdatableInfoScreen");
        t.child("Header", &self.header);
        t.child("Content", &self.paragraph);
        t.child("ActionBar", &self.action_bar);
    }
}
