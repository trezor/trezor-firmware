use heapless::Vec;

use crate::{
    error::Error,
    ui::{
        component::{
            text::paragraphs::{
                Paragraph, ParagraphSource, ParagraphStrType, ParagraphVecShort, Paragraphs, VecExt,
            },
            Component, Event, EventCtx, Never, Paginate, Qr,
        },
        geometry::Rect,
    },
};

use super::{theme, Frame};

pub struct AddressDetails<T> {
    qr_code: Frame<Qr, T>,
    details: Frame<Paragraphs<ParagraphVecShort<T>>, T>,
    xpub_view: Frame<Paragraphs<Paragraph<T>>, T>,
    xpubs: Vec<(T, T), 16>,
    current_page: usize,
}

impl<T> AddressDetails<T>
where
    T: ParagraphStrType + From<&'static str>,
{
    pub fn new(
        qr_address: T,
        case_sensitive: bool,
        account: Option<T>,
        path: Option<T>,
    ) -> Result<Self, Error> {
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
                "RECEIVE ADDRESS".into(),
                Qr::new(qr_address, case_sensitive)?.with_border(7),
            )
            .with_border(theme::borders_horizontal_scroll()),
            details: Frame::left_aligned(
                theme::label_title(),
                "RECEIVING TO".into(),
                para.into_paragraphs(),
            )
            .with_border(theme::borders_horizontal_scroll()),
            xpub_view: Frame::left_aligned(
                theme::label_title(),
                " \n ".into(),
                Paragraph::new(&theme::TEXT_XPUB, "".into()).into_paragraphs(),
            )
            .with_border(theme::borders_horizontal_scroll()),
            xpubs: Vec::new(),
            current_page: 0,
        };
        Ok(result)
    }

    pub fn add_xpub(&mut self, title: T, xpub: T) -> Result<(), Error> {
        self.xpubs
            .push((title, xpub))
            .map_err(|_| Error::OutOfRange)
    }
}

impl<T> Paginate for AddressDetails<T>
where
    T: ParagraphStrType + Clone,
{
    fn page_count(&mut self) -> usize {
        2 + self.xpubs.len()
    }

    fn change_page(&mut self, to_page: usize) {
        self.current_page = to_page;
        if to_page > 1 {
            let i = to_page - 2;
            // Context is needed for updating child so that it can request repaint. In this
            // case the parent component that handles paging always requests complete
            // repaint after page change so we can use a dummy context here.
            let mut dummy_ctx = EventCtx::new();
            self.xpub_view
                .update_title(&mut dummy_ctx, self.xpubs[i].0.clone());
            self.xpub_view.update_content(&mut dummy_ctx, |p| {
                p.inner_mut().update(self.xpubs[i].1.clone());
                p.change_page(0)
            });
        }
    }
}

impl<T> Component for AddressDetails<T>
where
    T: ParagraphStrType,
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.qr_code.place(bounds);
        self.details.place(bounds);
        self.xpub_view.place(bounds);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match self.current_page {
            0 => self.qr_code.event(ctx, event),
            1 => self.details.event(ctx, event),
            _ => self.xpub_view.event(ctx, event),
        }
    }

    fn paint(&mut self) {
        match self.current_page {
            0 => self.qr_code.paint(),
            1 => self.details.paint(),
            _ => self.xpub_view.paint(),
        }
    }

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
    T: ParagraphStrType + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("AddressDetails");
        match self.current_page {
            0 => self.qr_code.trace(t),
            1 => self.details.trace(t),
            _ => self.xpub_view.trace(t),
        }
        t.close();
    }
}
