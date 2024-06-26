use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::Rect,
    model_mercury::theme,
    shape::Renderer,
};

use super::{HoldToConfirm, TapToConfirm};

/// Component requesting an action from a user. Most typically embedded as a
/// content of a Frame and promptin "Tap to confirm" or "Hold to XYZ".
#[derive(Clone)]
pub enum PromptScreen {
    Tap(TapToConfirm),
    Hold(HoldToConfirm),
}

impl PromptScreen {
    pub fn new_hold_to_confirm() -> Self {
        PromptScreen::Hold(HoldToConfirm::new(theme::GREEN, theme::GREEN_LIGHT))
    }

    pub fn new_hold_to_confirm_danger() -> Self {
        PromptScreen::Hold(HoldToConfirm::new(theme::ORANGE_LIGHT, theme::ORANGE_LIGHT))
    }

    pub fn new_tap_to_confirm() -> Self {
        PromptScreen::Tap(TapToConfirm::new(
            theme::GREEN,
            theme::GREEN,
            theme::GREY_EXTRA_DARK,
            theme::GREEN_LIGHT,
            theme::ICON_SIMPLE_CHECKMARK,
        ))
    }

    pub fn new_tap_to_cancel() -> Self {
        PromptScreen::Tap(TapToConfirm::new(
            theme::ORANGE_LIGHT,
            theme::ORANGE_LIGHT,
            theme::GREY_EXTRA_DARK,
            theme::ORANGE_DIMMED,
            theme::ICON_SIMPLE_CHECKMARK,
        ))
    }

    pub fn new_tap_to_start() -> Self {
        PromptScreen::Tap(TapToConfirm::new(
            theme::GREY,
            theme::GREY,
            theme::GREY_EXTRA_DARK,
            theme::GREY_LIGHT,
            theme::ICON_CHEVRON_RIGHT,
        ))
    }
}

impl Component for PromptScreen {
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        match self {
            PromptScreen::Tap(t) => t.place(bounds),
            PromptScreen::Hold(h) => h.place(bounds),
        }
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match self {
            PromptScreen::Tap(t) => t.event(ctx, event),
            PromptScreen::Hold(h) => h.event(ctx, event),
        }
    }

    fn paint(&mut self) {
        todo!()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        match self {
            PromptScreen::Tap(t) => t.render(target),
            PromptScreen::Hold(h) => h.render(target),
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PromptScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("PromptScreen");
        match self {
            PromptScreen::Tap(c) => t.child("TapToConfirm", c),
            PromptScreen::Hold(c) => t.child("HoldToConfirm", c),
        }
    }
}
