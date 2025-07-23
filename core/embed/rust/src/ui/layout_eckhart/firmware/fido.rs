use crate::{
    strutil::TString,
    ui::{
        component::{
            image::Image,
            paginated::SinglePage,
            text::{
                paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs},
                TextStyle,
            },
            Component, Event, EventCtx, LineBreaking, Never,
        },
        geometry::{LinearPlacement, Rect},
        shape::Renderer,
    },
};

use super::super::{firmware::fido_icons::get_fido_icon_data, theme};

pub trait FidoAccountName: Fn() -> TString<'static> {}
impl<T: Fn() -> TString<'static>> FidoAccountName for T {}

pub struct FidoCredential<F: FidoAccountName> {
    app_icon: Option<Image>,
    text: Paragraphs<ParagraphVecShort<'static>>,
    get_account: F,
}

impl<F: FidoAccountName> FidoCredential<F> {
    const ICON_SIZE: i16 = 32;

    pub fn new(
        icon_name: Option<TString<'static>>,
        app_name: TString<'static>,
        get_account: F,
    ) -> Self {
        // Text style without line-breaking hyphens
        const STYLE: TextStyle =
            theme::TEXT_REGULAR.with_line_breaking(LineBreaking::BreakWordsNoHyphen);
        let app_icon = get_fido_icon_data(icon_name).map(Image::new);
        let text = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_MEDIUM_GREY, app_name),
            Paragraph::new(&STYLE, (get_account)()),
        ])
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical())
        .with_spacing(theme::TEXT_VERTICAL_SPACING);
        Self {
            app_icon,
            text,
            get_account,
        }
    }
}

impl<F: FidoAccountName> Component for FidoCredential<F> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        let text_area = if let Some(app_icon) = &mut self.app_icon {
            let icon_size = app_icon.toif.size();
            let (icon_area, text_area) =
                bounds.split_top(icon_size.y + theme::TEXT_VERTICAL_SPACING);
            app_icon.place(icon_area.with_width(icon_size.x).with_height(icon_size.y));
            text_area
        } else {
            bounds
        };

        self.text.place(text_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Event::Attach(_) = event {
            self.text.mutate(|p| p[1].update((self.get_account)()));
            ctx.request_paint();
        }
        self.app_icon.event(ctx, event);
        self.text.event(ctx, event);
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.app_icon.render(target);
        self.text.render(target);
    }
}

impl<F: FidoAccountName> SinglePage for FidoCredential<F> {}

#[cfg(feature = "ui_debug")]
impl<F: FidoAccountName> crate::trace::Trace for FidoCredential<F> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("FidoCredential");
        if let Some(app_icon) = self.app_icon.as_ref() {
            t.child("app_icon", app_icon);
        }
        t.child("paragraphs", &self.text);
    }
}
