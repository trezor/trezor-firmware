use crate::{
    strutil::TString,
    ui::{
        component::{text::TextStyle, Component, Event, EventCtx, Label},
        display::Icon,
        geometry::{Alignment, Insets, Rect},
        model_mercury::{
            component::{Button, ButtonMsg, ButtonStyleSheet},
            theme,
            theme::TITLE_HEIGHT,
        },
        shape::Renderer,
    },
};

const BUTTON_EXPAND_BORDER: i16 = 32;
#[derive(Clone)]
pub struct Header {
    area: Rect,
    title: Label<'static>,
    subtitle: Option<Label<'static>>,
    button: Option<Button>,
}

impl Header {
    pub const fn new(alignment: Alignment, title: TString<'static>) -> Self {
        Self {
            area: Rect::zero(),
            title: Label::new(title, alignment, theme::label_title_main()).vertically_centered(),
            subtitle: None,
            button: None,
        }
    }

    pub fn with_subtitle(mut self, subtitle: TString<'static>) -> Self {
        let style = theme::TEXT_SUB_GREY;
        self.title = self.title.top_aligned();
        self.subtitle = Some(Label::new(subtitle, self.title.alignment(), style));
        self
    }

    pub fn styled(mut self, style: TextStyle) -> Self {
        self.title = self.title.styled(style);
        self
    }

    pub fn subtitle_styled(mut self, style: TextStyle) -> Self {
        if let Some(subtitle) = self.subtitle.take() {
            self.subtitle = Some(subtitle.styled(style))
        }
        self
    }

    pub fn update_title(&mut self, title: TString<'static>) {
        self.title.set_text(title);
    }

    pub fn update_subtitle(
        &mut self,
        new_subtitle: TString<'static>,
        new_style: Option<TextStyle>,
    ) {
        let style = new_style.unwrap_or(theme::TEXT_SUB_GREY);
        match &mut self.subtitle {
            Some(subtitle) => {
                subtitle.set_style(style);
                subtitle.set_text(new_subtitle);
            }
            None => {
                self.subtitle = Some(Label::new(new_subtitle, self.title.alignment(), style));
            }
        }
    }

    pub fn with_button(mut self, icon: Icon, enabled: bool) -> Self {
        let touch_area = Insets::uniform(BUTTON_EXPAND_BORDER);
        self.button = Some(
            Button::with_icon(icon)
                .with_expanded_touch_area(touch_area)
                .initially_enabled(enabled)
                .styled(theme::button_default()),
        );
        self
    }

    pub fn button_styled(mut self, style: ButtonStyleSheet) -> Self {
        if self.button.is_some() {
            self.button = Some(self.button.unwrap().styled(style));
        }
        self
    }
}

impl Component for Header {
    type Msg = ButtonMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let header_area = if let Some(b) = &mut self.button {
            let (rest, button_area) = bounds.split_right(TITLE_HEIGHT);
            b.place(button_area);
            rest
        } else {
            bounds
        };

        if self.subtitle.is_some() {
            let title_area = self.title.place(header_area);
            let remaining = header_area.inset(Insets::top(title_area.height()));
            let _subtitle_area = self.subtitle.place(remaining);
        } else {
            self.title.place(header_area);
        }

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.title.event(ctx, event);
        self.subtitle.event(ctx, event);

        self.button.event(ctx, event)
    }

    fn paint(&mut self) {
        todo!()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.button.render(target);
        self.title.render(target);
        self.subtitle.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Header {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Header");
        t.child("title", &self.title);
        if let Some(subtitle) = &self.subtitle {
            t.child("subtitle", subtitle);
        }

        if let Some(button) = &self.button {
            t.child("button", button);
        }
    }
}
