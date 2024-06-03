use heapless::Vec;

use crate::{
    error::Error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs, VecExt},
            Component, Event, EventCtx, Paginate,
        },
        geometry::Rect,
        shape::Renderer,
    },
};

use super::{theme, Frame, FrameMsg};

const MAX_XPUBS: usize = 16;

#[derive(Clone)]
pub struct AddressDetails {
    details: Frame<Paragraphs<ParagraphVecShort<'static>>>,
    xpub_view: Frame<Paragraphs<Paragraph<'static>>>,
    xpubs: Vec<(TString<'static>, TString<'static>), MAX_XPUBS>,
    xpub_page_count: Vec<u8, MAX_XPUBS>,
    current_page: usize,
}

impl AddressDetails {
    pub fn new(
        details_title: TString<'static>,
        account: Option<TString<'static>>,
        path: Option<TString<'static>>,
    ) -> Result<Self, Error> {
        let mut para = ParagraphVecShort::new();
        if let Some(a) = account {
            para.add(Paragraph::new::<TString>(
                &theme::TEXT_SUB_GREY,
                TR::words__account.into(),
            ));
            para.add(Paragraph::new(&theme::TEXT_MONO_GREY_LIGHT, a));
        }
        if account.is_some() & path.is_some() {
            para.add(Paragraph::new(
                &theme::TEXT_SUB_GREY,
                TString::from_str(" "),
            ));
        }
        if let Some(p) = path {
            para.add(Paragraph::new::<TString>(
                &theme::TEXT_SUB_GREY,
                TR::address_details__derivation_path.into(),
            ));
            para.add(Paragraph::new(&theme::TEXT_MONO_GREY_LIGHT, p));
        }
        let result = Self {
            details: Frame::left_aligned(details_title, para.into_paragraphs())
                .with_cancel_button(),
            xpub_view: Frame::left_aligned(
                " \n ".into(),
                Paragraph::new(&theme::TEXT_MONO_GREY_LIGHT, "").into_paragraphs(),
            )
            .with_cancel_button(),
            xpubs: Vec::new(),
            xpub_page_count: Vec::new(),
            current_page: 0,
        };
        Ok(result)
    }

    pub fn add_xpub(
        &mut self,
        title: TString<'static>,
        xpub: TString<'static>,
    ) -> Result<(), Error> {
        self.xpubs
            .push((title, xpub))
            .map_err(|_| Error::OutOfRange)
    }

    fn switch_xpub(&mut self, i: usize, page: usize) -> usize {
        // Context is needed for updating child so that it can request repaint. In this
        // case the parent component that handles paging always requests complete
        // repaint after page change so we can use a dummy context here.
        let mut dummy_ctx = EventCtx::new();
        self.xpub_view.update_title(&mut dummy_ctx, self.xpubs[i].0);
        self.xpub_view.update_content(&mut dummy_ctx, |_ctx, p| {
            p.inner_mut().update(self.xpubs[i].1);
            let npages = p.page_count();
            p.change_page(page);
            npages
        })
    }

    fn lookup(&self, scrollbar_page: usize) -> (usize, usize) {
        let mut xpub_index = 0;
        let mut xpub_page = scrollbar_page;
        for page_count in self.xpub_page_count.iter().map(|pc| {
            let upc: usize = (*pc).into();
            upc
        }) {
            if page_count <= xpub_page {
                xpub_page -= page_count;
                xpub_index += 1;
            } else {
                break;
            }
        }
        (xpub_index, xpub_page)
    }
}

impl Paginate for AddressDetails {
    fn page_count(&mut self) -> usize {
        let total_xpub_pages: u8 = self.xpub_page_count.iter().copied().sum();
        1usize.saturating_add(total_xpub_pages.into())
    }

    fn change_page(&mut self, to_page: usize) {
        self.current_page = to_page;
        if to_page > 0 {
            let i = to_page - 1;
            let (xpub_index, xpub_page) = self.lookup(i);
            self.switch_xpub(xpub_index, xpub_page);
        }
    }
}

impl Component for AddressDetails {
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        self.details.place(bounds);
        self.xpub_view.place(bounds);

        self.xpub_page_count.clear();
        for i in 0..self.xpubs.len() {
            let npages = self.switch_xpub(i, 0) as u8;
            unwrap!(self.xpub_page_count.push(npages));
        }

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let msg = match self.current_page {
            0 => self.details.event(ctx, event),
            _ => self.xpub_view.event(ctx, event),
        };
        match msg {
            Some(FrameMsg::Button(_)) => Some(()),
            _ => None,
        }
    }

    fn paint(&mut self) {
        match self.current_page {
            0 => self.details.paint(),
            _ => self.xpub_view.paint(),
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        match self.current_page {
            0 => self.details.render(target),
            _ => self.xpub_view.render(target),
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        match self.current_page {
            0 => self.details.bounds(sink),
            _ => self.xpub_view.bounds(sink),
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for AddressDetails {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("AddressDetails");
        match self.current_page {
            0 => t.child("details", &self.details),
            _ => t.child("xpub_view", &self.xpub_view),
        }
    }
}
