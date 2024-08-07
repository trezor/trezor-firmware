use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::Rect,
    shape::Renderer,
};

use super::{super::theme, BinarySelection, ButtonContent, HoldToConfirm, TapToConfirm};

/// Component requesting an action from a user. Most typically embedded as a
/// content of a Frame. Options are:
///     - Tap to confirm
///     - Hold to confirm
///     - Yes/No selection
#[derive(Clone)]
pub enum PromptScreen {
    Tap(TapToConfirm),
    Hold(HoldToConfirm),
    Choose(BinarySelection),
}

pub enum PromptMsg {
    Confirmed,
    Cancelled,
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
            theme::ICON_SIMPLE_CHECKMARK30,
        ))
    }

    pub fn new_tap_to_cancel() -> Self {
        PromptScreen::Tap(TapToConfirm::new(
            theme::ORANGE_LIGHT,
            theme::ORANGE_LIGHT,
            theme::GREY_EXTRA_DARK,
            theme::ORANGE_DIMMED,
            theme::ICON_SIMPLE_CHECKMARK30,
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

    pub fn new_yes_or_no() -> Self {
        PromptScreen::Choose(BinarySelection::new(
            ButtonContent::Icon(theme::ICON_CLOSE),
            ButtonContent::Icon(theme::ICON_SIMPLE_CHECKMARK30),
            theme::button_cancel(),
            theme::button_confirm(),
        ))
    }
}

impl Component for PromptScreen {
    type Msg = PromptMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        match self {
            PromptScreen::Tap(t) => t.place(bounds),
            PromptScreen::Hold(h) => h.place(bounds),
            PromptScreen::Choose(c) => c.place(bounds),
        }
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match self {
            PromptScreen::Tap(_) | PromptScreen::Hold(_) => {
                let res = match self {
                    PromptScreen::Tap(t) => t.event(ctx, event),
                    PromptScreen::Hold(h) => h.event(ctx, event),
                    _ => None,
                };
                if res.is_some() {
                    return Some(PromptMsg::Confirmed);
                }
            }
            PromptScreen::Choose(c) => {
                if let Some(res) = c.event(ctx, event) {
                    match res {
                        super::BinarySelectionMsg::Left => return Some(PromptMsg::Cancelled),
                        super::BinarySelectionMsg::Right => return Some(PromptMsg::Confirmed),
                    }
                }
            }
        }
        None
    }

    fn paint(&mut self) {
        todo!()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        match self {
            PromptScreen::Tap(t) => t.render(target),
            PromptScreen::Hold(h) => h.render(target),
            PromptScreen::Choose(c) => c.render(target),
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PromptScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("PromptScreen");
        match self {
            PromptScreen::Tap(c) => t.child("TapToConfirm", c),
            PromptScreen::Hold(h) => t.child("HoldToConfirm", h),
            PromptScreen::Choose(c) => t.child("ChooseBinarySelection", c),
        }
    }
}
