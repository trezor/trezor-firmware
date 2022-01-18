use crate::{
    time::Instant,
    ui::{
        component::{Child, Component, ComponentExt, Event, EventCtx, Pad},
        geometry::Rect,
    },
};

use super::{theme, Button, ButtonMsg, DialogLayout, Loader, LoaderMsg};

pub enum HoldToConfirmMsg<T> {
    Content(T),
    Cancelled,
    Confirmed,
}

pub struct HoldToConfirm<T> {
    loader: Loader,
    content: Child<T>,
    cancel: Child<Button<&'static str>>,
    confirm: Child<Button<&'static str>>,
    pad: Pad,
}

impl<T> HoldToConfirm<T>
where
    T: Component,
{
    pub fn new(area: Rect, content: impl FnOnce(Rect) -> T) -> Self {
        let layout = DialogLayout::middle(area);
        Self {
            loader: Loader::new(0),
            content: content(layout.content).into_child(),
            cancel: Button::with_text(layout.left, "Cancel").into_child(),
            confirm: Button::with_text(layout.right, "Hold").into_child(),
            pad: Pad::with_background(layout.content, theme::BG),
        }
    }
}

impl<T> Component for HoldToConfirm<T>
where
    T: Component,
{
    type Msg = HoldToConfirmMsg<T::Msg>;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let now = Instant::now();

        if let Some(LoaderMsg::ShrunkCompletely) = self.loader.event(ctx, event) {
            // Clear the remnants of the loader.
            self.pad.clear();
            // Switch it to the initial state, so we stop painting it.
            self.loader.reset();
            // Re-draw the whole content tree.
            self.content.request_complete_repaint(ctx);
            // This can be a result of an animation frame event, we should take
            // care to not short-circuit here and deliver the event to the
            // content as well.
        }
        if let Some(msg) = self.content.event(ctx, event) {
            return Some(Self::Msg::Content(msg));
        }
        if let Some(ButtonMsg::Clicked) = self.cancel.event(ctx, event) {
            return Some(Self::Msg::Cancelled);
        }
        match self.confirm.event(ctx, event) {
            Some(ButtonMsg::Pressed) => {
                self.loader.start_growing(ctx, now);
                self.pad.clear(); // Clear the remnants of the content.
            }
            Some(ButtonMsg::Released) => {
                self.loader.start_shrinking(ctx, now);
            }
            Some(ButtonMsg::Clicked) => {
                if self.loader.is_completely_grown(now) {
                    self.loader.reset();
                    return Some(HoldToConfirmMsg::Confirmed);
                } else {
                    self.loader.start_shrinking(ctx, now);
                }
            }
            _ => {}
        }

        None
    }

    fn paint(&mut self) {
        self.pad.paint();
        if self.loader.is_animating() {
            self.loader.paint();
        } else {
            self.content.paint();
        }
        self.cancel.paint();
        self.confirm.paint();
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for HoldToConfirm<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, d: &mut dyn crate::trace::Tracer) {
        d.open("HoldToConfirm");
        self.content.trace(d);
        d.close();
    }
}
