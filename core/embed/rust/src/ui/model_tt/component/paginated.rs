use crate::ui::{
    component::{
        text::layout::{LayoutFit, TextNoOp},
        Component, ComponentExt, Event, EventCtx, FormattedText, Pad,
    },
    display,
    geometry::Rect,
};

use super::{
    page::{Page, PageMsg},
    theme,
};

pub struct Paginated<T> {
    page: Page<T>,
    pad: Pad,
    fade_after_next_paint: Option<i32>,
}

impl<T> Paginated<T>
where
    T: Paginate,
{
    pub fn new(area: Rect, mut content: T) -> Self {
        let active_page = 0;
        let page_count = content.page_count();
        Self {
            page: Page::new(area, content, page_count, active_page),
            pad: Pad::with_background(area, theme::BG),
            fade_after_next_paint: None,
        }
    }
}

impl<T> Component for Paginated<T>
where
    T: Paginate,
    T: Component,
{
    type Msg = T::Msg;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.page.event(ctx, event).and_then(|msg| match msg {
            PageMsg::Content(c) => Some(c),
            PageMsg::ChangePage(page) => {
                self.fade_after_next_paint = Some(theme::BACKLIGHT_NORMAL);
                self.page.inner_mut().change_page(page);
                self.page.inner_mut().request_complete_repaint(ctx);
                self.pad.clear();
                None
            }
        })
    }

    fn paint(&mut self) {
        self.pad.paint();
        self.page.paint();
        if let Some(val) = self.fade_after_next_paint.take() {
            display::fade_backlight(val);
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Paginated<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.page.trace(t);
    }
}

pub trait Paginate {
    fn page_count(&mut self) -> usize;
    fn change_page(&mut self, active_page: usize);
}

impl<F, T> Paginate for FormattedText<F, T>
where
    F: AsRef<[u8]>,
    T: AsRef<[u8]>,
{
    fn page_count(&mut self) -> usize {
        let mut page_count = 1; // There's always at least one page.
        let mut char_offset = 0;

        loop {
            let fit = self.layout_content(&mut TextNoOp);
            match fit {
                LayoutFit::Fitting { .. } => {
                    break; // TODO: We should consider if there's more content
                           // to render.
                }
                LayoutFit::OutOfBounds { processed_chars } => {
                    page_count += 1;
                    char_offset += processed_chars;
                    self.set_char_offset(char_offset);
                }
            }
        }

        // Reset the char offset back to the beginning.
        self.set_char_offset(0);

        page_count
    }

    fn change_page(&mut self, to_page: usize) {
        let mut active_page = 0;
        let mut char_offset = 0;

        // Make sure we're starting from the beginning.
        self.set_char_offset(char_offset);

        while active_page < to_page {
            let fit = self.layout_content(&mut TextNoOp);
            match fit {
                LayoutFit::Fitting { .. } => {
                    break; // TODO: We should consider if there's more content
                           // to render.
                }
                LayoutFit::OutOfBounds { processed_chars } => {
                    active_page += 1;
                    char_offset += processed_chars;
                    self.set_char_offset(char_offset);
                }
            }
        }
    }
}
