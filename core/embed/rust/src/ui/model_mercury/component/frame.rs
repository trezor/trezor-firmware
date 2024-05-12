use crate::{
    strutil::TString,
    ui::{
        component::{
            base::ComponentExt, label::Label, text::TextStyle, Child, Component, Event, EventCtx,
        },
        display::Icon,
        geometry::{Alignment, Insets, Rect},
        shape::Renderer,
    },
};

use super::{theme, Button, ButtonMsg, ButtonStyleSheet, CancelInfoConfirmMsg, Footer};

const TITLE_HEIGHT: i16 = 42;
const BUTTON_EXPAND_BORDER: i16 = 32;

#[derive(Clone)]
pub struct Frame<T> {
    border: Insets,
    title: Child<Label<'static>>,
    subtitle: Option<Child<Label<'static>>>,
    button: Option<Child<Button>>,
    button_msg: CancelInfoConfirmMsg,
    content: Child<T>,
    footer: Option<Footer<'static>>,
}

pub enum FrameMsg<T> {
    Content(T),
    Button(CancelInfoConfirmMsg),
}

impl<T> Frame<T>
where
    T: Component,
{
    pub const fn new(alignment: Alignment, title: TString<'static>, content: T) -> Self {
        Self {
            title: Child::new(
                Label::new(title, alignment, theme::label_title_main()).vertically_centered(),
            ),
            subtitle: None,
            border: theme::borders(),
            button: None,
            button_msg: CancelInfoConfirmMsg::Cancelled,
            content: Child::new(content),
            footer: None,
        }
    }

    pub const fn left_aligned(title: TString<'static>, content: T) -> Self {
        Self::new(Alignment::Start, title, content)
    }

    pub const fn right_aligned(title: TString<'static>, content: T) -> Self {
        Self::new(Alignment::End, title, content)
    }

    pub const fn centered(title: TString<'static>, content: T) -> Self {
        Self::new(Alignment::Center, title, content)
    }

    pub const fn with_border(mut self, border: Insets) -> Self {
        self.border = border;
        self
    }

    pub fn title_styled(mut self, style: TextStyle) -> Self {
        self.title = Child::new(self.title.into_inner().styled(style));
        self
    }

    pub fn with_subtitle(mut self, subtitle: TString<'static>) -> Self {
        let style = theme::TEXT_SUB_GREY;
        self.title = Child::new(self.title.into_inner().top_aligned());
        self.subtitle = Some(Child::new(Label::new(
            subtitle,
            self.title.inner().alignment(),
            style,
        )));
        self
    }

    fn with_button(mut self, icon: Icon, msg: CancelInfoConfirmMsg, enabled: bool) -> Self {
        let touch_area = Insets::uniform(BUTTON_EXPAND_BORDER);
        self.button = Some(Child::new(
            Button::with_icon(icon)
                .with_expanded_touch_area(touch_area)
                .initially_enabled(enabled)
                .styled(theme::button_default()),
        ));
        self.button_msg = msg;
        self
    }

    pub fn with_cancel_button(self) -> Self {
        self.with_button(theme::ICON_CLOSE, CancelInfoConfirmMsg::Cancelled, true)
    }

    pub fn with_menu_button(self) -> Self {
        self.with_button(theme::ICON_MENU, CancelInfoConfirmMsg::Info, true)
    }

    pub fn with_warning_button(self) -> Self {
        self.with_button(theme::ICON_WARNING, CancelInfoConfirmMsg::Info, false)
            .button_styled(theme::button_danger())
    }

    pub fn button_styled(mut self, style: ButtonStyleSheet) -> Self {
        if self.button.is_some() {
            self.button = Some(Child::new(self.button.unwrap().into_inner().styled(style)));
        }
        self
    }

    pub fn with_footer(
        mut self,
        instruction: TString<'static>,
        description: Option<TString<'static>>,
    ) -> Self {
        let mut footer = Footer::new(instruction);
        if let Some(description_text) = description {
            footer = footer.with_description(description_text);
        }
        self.footer = Some(footer);
        self
    }

    pub fn with_danger(self) -> Self {
        self.button_styled(theme::button_danger())
            .title_styled(theme::label_title_danger())
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }

    pub fn update_title(&mut self, ctx: &mut EventCtx, new_title: TString<'static>) {
        self.title.mutate(ctx, |ctx, t| {
            t.set_text(new_title);
            t.request_complete_repaint(ctx)
        })
    }

    pub fn update_content<F, R>(&mut self, ctx: &mut EventCtx, update_fn: F) -> R
    where
        F: Fn(&mut EventCtx, &mut T) -> R,
    {
        self.content.mutate(ctx, |ctx, c| {
            let res = update_fn(ctx, c);
            c.request_complete_repaint(ctx);
            res
        })
    }
}

impl<T> Component for Frame<T>
where
    T: Component,
{
    type Msg = FrameMsg<T::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (mut header_area, mut content_area) = bounds.split_top(TITLE_HEIGHT);
        content_area = content_area.inset(Insets::top(theme::SPACING));
        header_area = header_area.inset(Insets::sides(theme::SPACING));

        if let Some(b) = &mut self.button {
            let (rest, button_area) = header_area.split_right(TITLE_HEIGHT);
            header_area = rest;
            b.place(button_area);
        }

        if self.subtitle.is_some() {
            let title_area = self.title.place(header_area);
            let remaining = header_area.inset(Insets::top(title_area.height()));
            let _subtitle_area = self.subtitle.place(remaining);
        } else {
            self.title.place(header_area);
        }

        if let Some(footer) = &mut self.footer {
            // FIXME: spacer at the bottom might be applied also for usage without footer
            // but not for VerticalMenu
            content_area = content_area.inset(Insets::bottom(theme::SPACING));
            let (remaining, footer_area) = content_area.split_bottom(footer.height());
            footer.place(footer_area);
            content_area = remaining;
        }
        self.content.place(content_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.title.event(ctx, event);
        self.subtitle.event(ctx, event);
        if let Some(ButtonMsg::Clicked) = self.button.event(ctx, event) {
            return Some(FrameMsg::Button(self.button_msg));
        }
        self.content.event(ctx, event).map(FrameMsg::Content)
    }

    fn paint(&mut self) {
        self.title.paint();
        self.subtitle.paint();
        self.button.paint();
        self.content.paint();
        self.footer.paint();
    }
    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.title.render(target);
        self.subtitle.render(target);
        self.button.render(target);
        self.content.render(target);
        self.footer.render(target);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.title.bounds(sink);
        self.subtitle.bounds(sink);
        self.button.bounds(sink);
        self.content.bounds(sink);
        self.footer.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Frame<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Frame");
        t.child("title", &self.title);
        t.child("content", &self.content);
        if let Some(subtitle) = &self.subtitle {
            t.child("subtitle", subtitle);
        }
        if let Some(button) = &self.button {
            t.child("button", button);
        }
        if let Some(footer) = &self.footer {
            t.child("footer", footer);
        }
    }
}

#[cfg(feature = "micropython")]
impl<T> crate::ui::flow::Swipable for Frame<T>
where
    T: Component + crate::ui::flow::Swipable,
{
    fn swipe_start(
        &mut self,
        ctx: &mut EventCtx,
        direction: crate::ui::component::SwipeDirection,
    ) -> bool {
        self.update_content(ctx, |ctx, inner| inner.swipe_start(ctx, direction))
    }

    fn swipe_finished(&self) -> bool {
        self.inner().swipe_finished()
    }
}
