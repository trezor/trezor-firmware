use crate::{
    strutil::TString,
    ui::{
        component::{
            paginated::Paginate,
            text::paragraphs::{Paragraph, Paragraphs},
            Component, Event, EventCtx, Never,
        },
        geometry::Rect,
        shape::Renderer,
    },
};

use super::theme;

pub struct UpdatableMoreInfo<F>
where
    F: Fn() -> TString<'static>,
{
    info_func: F,
    paragraphs: Paragraphs<Paragraph<'static>>,
}

impl<F> UpdatableMoreInfo<F>
where
    F: Fn() -> TString<'static>,
{
    pub fn new(info_func: F) -> Self {
        Self {
            info_func,
            paragraphs: Paragraphs::new(Paragraph::new(
                &theme::TEXT_MAIN_GREY_LIGHT,
                TString::empty(),
            )),
        }
    }

    fn update_text(&mut self, ctx: &mut EventCtx) {
        let text = (self.info_func)();
        self.paragraphs.inner_mut().update(text);
        self.paragraphs.change_page(0);
        ctx.request_paint();
    }
}

impl<F> Component for UpdatableMoreInfo<F>
where
    F: Fn() -> TString<'static>,
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.paragraphs.place(bounds);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Attach(_) = event {
            self.update_text(ctx);
        }
        None
    }

    fn paint(&mut self) {
        todo!("remove when ui-t3t1 done");
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.paragraphs.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl<F> crate::trace::Trace for UpdatableMoreInfo<F>
where
    F: Fn() -> TString<'static>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("UpdatableMoreInfo");
        t.child("paragraphs", &self.paragraphs);
    }
}
