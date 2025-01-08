use crate::{
    strutil::TString,
    time::{Duration, Instant},
    ui::{
        component::{Component, Event, EventCtx},
        event::ButtonEvent,
        geometry::Rect,
        shape::Renderer,
    },
};

use super::{
    loader::{Loader, DEFAULT_DURATION_MS},
    theme, ButtonContent, ButtonDetails, ButtonPos, LoaderMsg, LoaderStyleSheet,
};

pub enum HoldToConfirmMsg {
    Confirmed,
    FailedToConfirm,
}

pub struct HoldToConfirm {
    pos: ButtonPos,
    loader: Loader,
    text_width: i16,
}

impl HoldToConfirm {
    pub fn text<T: Into<TString<'static>>>(
        pos: ButtonPos,
        text: T,
        styles: LoaderStyleSheet,
        duration: Duration,
    ) -> Self {
        let text = text.into();
        let text_width = text.map(|t| styles.normal.font.visible_text_width(t));
        Self {
            pos,
            loader: Loader::text(text, styles).with_growing_duration(duration),
            text_width,
        }
    }

    pub fn from_button_details(pos: ButtonPos, btn_details: ButtonDetails) -> Self {
        let duration = btn_details
            .duration
            .unwrap_or_else(|| Duration::from_millis(DEFAULT_DURATION_MS));
        match btn_details.content {
            ButtonContent::Text(text) => {
                Self::text(pos, text, LoaderStyleSheet::default_loader(), duration)
            }
            ButtonContent::Icon(_) => fatal_error!("Icon is not supported"),
        }
    }

    /// Updating the text of the component and re-placing it.
    pub fn set_text<T: Into<TString<'static>>>(&mut self, text: T, button_area: Rect) {
        let text = text.into();
        self.text_width = self.loader.get_text_width(&text);
        self.loader.set_text(text);
        self.place(button_area);
    }

    pub fn reset(&mut self) {
        self.loader.reset();
    }

    pub fn set_duration(&mut self, duration: Duration) {
        self.loader.set_duration(duration);
    }

    pub fn get_duration(&self) -> Duration {
        self.loader.get_duration()
    }

    pub fn get_text(&self) -> TString<'static> {
        self.loader.get_text()
    }

    fn placement(&mut self, area: Rect, pos: ButtonPos) -> Rect {
        let button_width = self.text_width + 2 * theme::BUTTON_OUTLINE;
        match pos {
            ButtonPos::Left => area.split_left(button_width).0,
            ButtonPos::Right => area.split_right(button_width).1,
            ButtonPos::Middle => area.split_center(button_width).1,
        }
    }
}

impl Component for HoldToConfirm {
    type Msg = HoldToConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let loader_area = self.placement(bounds, self.pos);
        self.loader.place(loader_area)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            Event::Button(ButtonEvent::HoldStarted) => {
                self.loader.start_growing(ctx, Instant::now());
            }
            Event::Button(ButtonEvent::HoldEnded) => {
                if self.loader.is_animating() {
                    self.loader.start_shrinking(ctx, Instant::now());
                }
            }
            _ => {}
        };

        let msg = self.loader.event(ctx, event);

        if let Some(LoaderMsg::GrownCompletely) = msg {
            return Some(HoldToConfirmMsg::Confirmed);
        }
        if let Some(LoaderMsg::ShrunkCompletely) = msg {
            return Some(HoldToConfirmMsg::FailedToConfirm);
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.loader.render(target);
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for HoldToConfirm {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("HoldToConfirm");
        t.child("loader", &self.loader);
    }
}
