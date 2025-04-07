use crate::{
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeConfig,
            text::paragraphs::{Paragraph, ParagraphSource, Paragraphs},
            Component, Event, EventCtx,
        },
        flow::Swipable,
        geometry::{LinearPlacement, Rect},
        shape::Renderer,
        util::Pager,
    },
};

use super::{theme, Header, TextScreen, TextScreenMsg};

pub struct UpdatableInfoScreen<F>
where
    F: Fn() -> TString<'static>,
{
    info_func: F,
    paragraphs: Paragraphs<Paragraph<'static>>,
    area: Rect,
    text_screen: TextScreen<Paragraphs<Paragraph<'static>>>,
}

impl<F> UpdatableInfoScreen<F>
where
    F: Fn() -> TString<'static>,
{
    pub fn new(info_func: F) -> Self {
        let paragraphs = Paragraph::new(&theme::TEXT_REGULAR, TString::empty())
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical());
        let text_screen = create_text_screen(paragraphs.clone());
        Self {
            info_func,
            paragraphs,
            area: Rect::zero(),
            text_screen,
        }
    }

    fn update_text(&mut self, ctx: &mut EventCtx) {
        let text = (self.info_func)();
        self.paragraphs.update(text);
        self.text_screen = create_text_screen(self.paragraphs.clone());
        self.text_screen.place(self.area);
        ctx.request_paint();
    }
}

impl<F> Component for UpdatableInfoScreen<F>
where
    F: Fn() -> TString<'static>,
{
    type Msg = TextScreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.text_screen.place(bounds);
        self.area = bounds;
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Attach(_) = event {
            self.update_text(ctx);
        }

        self.text_screen.event(ctx, event)
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.text_screen.render(target);
    }
}

fn create_text_screen(
    paragraphs: Paragraphs<Paragraph<'static>>,
) -> TextScreen<Paragraphs<Paragraph<'static>>> {
    TextScreen::new(paragraphs)
        .with_header(Header::new(TR::buttons__more_info.into()).with_close_button())
}

impl<F: Fn() -> TString<'static>> Swipable for UpdatableInfoScreen<F> {
    fn get_pager(&self) -> Pager {
        Pager::single_page()
    }
    fn get_swipe_config(&self) -> SwipeConfig {
        SwipeConfig::default()
    }
}

#[cfg(feature = "ui_debug")]
impl<F> crate::trace::Trace for UpdatableInfoScreen<F>
where
    F: Fn() -> TString<'static>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("UpdatableInfoScreen");
        t.child("screen", &self.text_screen);
    }
}
