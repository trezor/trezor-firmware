use heapless::Vec;

use crate::{
    error::Error,
    strutil::StringType,
    ui::{
        component::{
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs, VecExt},
            Component, Event, EventCtx, Paginate, Qr,
        },
        geometry::Rect,
    },
};

use super::{theme, Frame, FrameMsg};

const MAX_XPUBS: usize = 16;

pub struct AddressDetails<T> {
    qr_code: Frame<Qr, T>,
    details: Frame<Paragraphs<ParagraphVecShort<T>>, T>,
    xpub_view: Frame<Paragraphs<Paragraph<T>>, T>,
    xpubs: Vec<(T, T), MAX_XPUBS>,
    xpub_page_count: Vec<u8, MAX_XPUBS>,
    current_page: usize,
}

impl<T> AddressDetails<T>
where
    T: StringType,
{
    pub fn new(
        qr_title: T,
        qr_address: T,
        case_sensitive: bool,
        details_title: T,
        account: Option<T>,
        path: Option<T>,
    ) -> Result<Self, Error>
    where
        T: From<&'static str>,
    {
        let mut para = ParagraphVecShort::new();
        if let Some(a) = account {
            para.add(Paragraph::new(&theme::TEXT_NORMAL, "Account:".into()));
            para.add(Paragraph::new(&theme::TEXT_MONO, a));
        }
        if let Some(p) = path {
            para.add(Paragraph::new(
                &theme::TEXT_NORMAL,
                "Derivation path:".into(),
            ));
            para.add(Paragraph::new(&theme::TEXT_MONO, p));
        }
        let result = Self {
            qr_code: Frame::left_aligned(
                theme::label_title(),
                qr_title,
                Qr::new(qr_address, case_sensitive)?.with_border(7),
            )
            .with_cancel_button()
            .with_border(theme::borders_horizontal_scroll()),
            details: Frame::left_aligned(
                theme::label_title(),
                details_title,
                para.into_paragraphs(),
            )
            .with_cancel_button()
            .with_border(theme::borders_horizontal_scroll()),
            xpub_view: Frame::left_aligned(
                theme::label_title(),
                " \n ".into(),
                Paragraph::new(&theme::TEXT_MONO, "".into()).into_paragraphs(),
            )
            .with_cancel_button()
            .with_border(theme::borders_horizontal_scroll()),
            xpubs: Vec::new(),
            xpub_page_count: Vec::new(),
            current_page: 0,
        };
        Ok(result)
    }

    pub fn add_xpub(&mut self, title: T, xpub: T) -> Result<(), Error> {
        self.xpubs
            .push((title, xpub))
            .map_err(|_| Error::OutOfRange)
    }

    fn switch_xpub(&mut self, i: usize, page: usize) -> usize
    where
        T: Clone,
    {
        // Context is needed for updating child so that it can request repaint. In this
        // case the parent component that handles paging always requests complete
        // repaint after page change so we can use a dummy context here.
        let mut dummy_ctx = EventCtx::new();
        self.xpub_view
            .update_title(&mut dummy_ctx, self.xpubs[i].0.clone());
        self.xpub_view.update_content(&mut dummy_ctx, |p| {
            p.inner_mut().update(self.xpubs[i].1.clone());
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

impl<T> Paginate for AddressDetails<T>
where
    T: StringType + Clone,
{
    fn page_count(&mut self) -> usize {
        let total_xpub_pages: u8 = self.xpub_page_count.iter().copied().sum();
        2usize.saturating_add(total_xpub_pages.into())
    }

    fn change_page(&mut self, to_page: usize) {
        self.current_page = to_page;
        if to_page > 1 {
            let i = to_page - 2;
            let (xpub_index, xpub_page) = self.lookup(i);
            self.switch_xpub(xpub_index, xpub_page);
        }
    }
}

impl<T> Component for AddressDetails<T>
where
    T: StringType + Clone,
{
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        self.qr_code.place(bounds);
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
            0 => self.qr_code.event(ctx, event),
            1 => self.details.event(ctx, event),
            _ => self.xpub_view.event(ctx, event),
        };
        match msg {
            Some(FrameMsg::Button(_)) => Some(()),
            _ => None,
        }
    }

    fn paint(&mut self) {
        match self.current_page {
            0 => self.qr_code.paint(),
            1 => self.details.paint(),
            _ => self.xpub_view.paint(),
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        match self.current_page {
            0 => self.qr_code.bounds(sink),
            1 => self.details.bounds(sink),
            _ => self.xpub_view.bounds(sink),
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for AddressDetails<T>
where
    T: StringType,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("AddressDetails");
        match self.current_page {
            0 => t.child("qr_code", &self.qr_code),
            1 => t.child("details", &self.details),
            _ => t.child("xpub_view", &self.xpub_view),
        }
    }
}
