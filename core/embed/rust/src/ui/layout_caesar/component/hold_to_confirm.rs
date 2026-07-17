use super::loader::{Loader, DEFAULT_DURATION_MS};
use super::{theme, ButtonContent, ButtonDetails, LoaderMsg, LoaderStyleSheet};
use crate::time::{Duration, Instant};
use crate::ui::component::{Component, Event, EventCtx};
use crate::ui::event::ButtonEvent;
use crate::ui::geometry::Rect;
use crate::ui::shape::Renderer;

pub enum HoldToConfirmMsg {
    Confirmed,
}

pub struct HoldToConfirm {
    loader: Loader,
    text_width: i16,
}

impl HoldToConfirm {
    pub fn from_button_details(btn_details: ButtonDetails) -> Self {
        let duration = btn_details
            .duration
            .unwrap_or_else(|| Duration::from_millis(DEFAULT_DURATION_MS));
        match btn_details.content {
            ButtonContent::Text(text) => {
                let styles = LoaderStyleSheet::default_loader();
                let text_width = text.map(|t| styles.normal.font.visible_text_width(t));
                Self {
                    loader: Loader::text(text, styles).with_growing_duration(duration),
                    text_width,
                }
            }
            ButtonContent::Icon(_) => fatal_error!("Icon is not supported"),
        }
    }
}

impl Component for HoldToConfirm {
    type Msg = HoldToConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let button_width = self.text_width + 2 * theme::BUTTON_OUTLINE;
        let loader_area = bounds.split_right(button_width).1;
        self.loader.place(loader_area)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            Event::Button(ButtonEvent::HoldStarted) => {
                self.loader.start_growing(ctx, Instant::now());
            }
            Event::Button(ButtonEvent::HoldEnded) if self.loader.is_animating() => {
                self.loader.start_shrinking(ctx, Instant::now());
            }
            Event::Button(ButtonEvent::HoldCanceled) => {
                self.loader.shrink_completely(ctx, Instant::now());
            }
            _ => {}
        };

        let msg = self.loader.event(ctx, event);

        if let Some(LoaderMsg::GrownCompletely) = msg {
            return Some(HoldToConfirmMsg::Confirmed);
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
