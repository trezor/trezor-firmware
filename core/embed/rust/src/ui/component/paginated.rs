use crate::ui::{
    component::{
        text::layout::{LayoutFit, TextNoOp},
        Component, ComponentExt, Event, EventCtx, FormattedText, Pad,
    },
    display::Color,
    geometry::Rect,
};

pub trait Page {
    type Content;

    fn new(area: Rect, page: Self::Content, page_count: usize, active_page: usize) -> Self;

    fn inner_mut(&mut self) -> &mut Self::Content;
    fn page_count(&self) -> usize;
    fn active_page(&self) -> usize;
    fn fade_after_next_paint(&mut self);
}

pub enum PageMsg<T> {
    Content(T),
    ChangePage(usize),
}

pub struct Paginated<P> {
    page: P,
    pad: Pad,
}

impl<P> Paginated<P>
where
    P: Page,
    P::Content: Paginate,
{
    pub fn new(area: Rect, content: impl FnOnce(Rect) -> P::Content, background: Color) -> Self {
        let active_page = 0;
        let mut content = content(area);
        let page_count = content.page_count();
        Self {
            page: P::new(area, content, page_count, active_page),
            pad: Pad::with_background(area, background),
        }
    }
}

impl<P> Component for Paginated<P>
where
    P: Page,
    P: Component<Msg = PageMsg<<<P as Page>::Content as Component>::Msg>>,
    P::Content: Paginate,
    P::Content: Component,
{
    type Msg = <<P as Page>::Content as Component>::Msg;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.page.event(ctx, event).and_then(|msg| match msg {
            PageMsg::Content(c) => Some(c),
            PageMsg::ChangePage(page) => {
                self.page.fade_after_next_paint();
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
    }
}

#[cfg(feature = "ui_debug")]
impl<P> crate::trace::Trace for Paginated<P>
where
    P: Page + crate::trace::Trace,
    P::Content: crate::trace::Trace,
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
