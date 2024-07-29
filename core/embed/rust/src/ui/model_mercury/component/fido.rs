use crate::{
    strutil::TString,
    ui::{
        component::{
            image::Image,
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs},
            Component, Event, EventCtx,
        },
        geometry::{Insets, Offset, Rect},
        model_mercury::component::{fido_icons::get_fido_icon_data, theme},
        shape::Renderer,
    },
};

pub struct FidoCredential<F: Fn() -> TString<'static>> {
    app_icon: Option<Image>,
    text: Paragraphs<ParagraphVecShort<'static>>,
    get_account: F,
}

impl<F: Fn() -> TString<'static>> FidoCredential<F> {
    const ICON_SIZE: i16 = 32;
    const SPACING: i16 = 8;

    pub fn new(
        icon_name: Option<TString<'static>>,
        app_name: TString<'static>,
        get_account: F,
    ) -> Self {
        let app_icon = get_fido_icon_data(icon_name).map(Image::new);
        let text = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_SUB_GREY, app_name),
            Paragraph::new(&theme::TEXT_MAIN_GREY_EXTRA_LIGHT, (get_account)()),
        ])
        .into_paragraphs();
        Self {
            app_icon,
            text,
            get_account,
        }
    }
}

impl<F: Fn() -> TString<'static>> Component for FidoCredential<F> {
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        let icon_size = self.app_icon.map_or(Offset::zero(), |i| i.toif.size());
        let (icon_area, text_area) = bounds.split_top(icon_size.y);
        let text_area = text_area.inset(Insets::top(Self::SPACING));
        self.text.place(text_area);
        let text_height = self.text.area().height();
        let vertical_space = bounds.height() - icon_size.y - Self::SPACING - text_height;
        let off = Offset::y(vertical_space / 2);

        let icon_area = icon_area.with_width(icon_size.x).translate(off);
        let text_area = text_area.with_height(text_height).translate(off);
        self.app_icon.place(icon_area);
        self.text.place(text_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Attach(_) = event {
            self.text.inner_mut()[1].update((self.get_account)());
            ctx.request_paint();
        }
        self.app_icon.event(ctx, event);
        self.text.event(ctx, event);
        None
    }

    fn paint(&mut self) {
        unimplemented!()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.app_icon.render(target);
        self.text.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl<F: Fn() -> TString<'static>> crate::trace::Trace for FidoCredential<F> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("FidoCredential");
    }
}
