use crate::{
    time::Instant,
    ui::{
        component::{Child, Component, ComponentExt, Event, EventCtx, FixedHeightBar, Pad},
        geometry::{Grid, Insets, Rect},
        util::animation_disabled,
    },
};

use super::{theme, Button, ButtonMsg, ButtonStyleSheet, Loader, LoaderMsg};

pub enum HoldToConfirmMsg<T> {
    Content(T),
    Confirmed,
    Cancelled,
}

pub struct HoldToConfirm<T> {
    loader: Loader,
    content: Child<T>,
    buttons: Child<FixedHeightBar<CancelHold>>,
    pad: Pad,
}

impl<T> HoldToConfirm<T>
where
    T: Component,
{
    pub fn new(content: T) -> Self {
        Self {
            loader: Loader::new(),
            content: Child::new(content),
            buttons: Child::new(CancelHold::new(theme::button_confirm())),
            pad: Pad::with_background(theme::BG),
        }
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }
}

impl<T> Component for HoldToConfirm<T>
where
    T: Component,
{
    type Msg = HoldToConfirmMsg<T::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        let controls_area = self.buttons.place(bounds);
        let content_area = bounds
            .inset(Insets::bottom(controls_area.height()))
            .inset(Insets::bottom(theme::BUTTON_SPACING))
            .inset(Insets::left(theme::CONTENT_BORDER));
        self.pad.place(content_area);
        self.loader.place(content_area);
        self.content.place(content_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(msg) = self.content.event(ctx, event) {
            return Some(HoldToConfirmMsg::Content(msg));
        }
        let button_msg = match self.buttons.event(ctx, event) {
            Some(CancelHoldMsg::Cancelled) => return Some(HoldToConfirmMsg::Cancelled),
            Some(CancelHoldMsg::HoldButton(b)) => Some(b),
            _ => None,
        };
        if handle_hold_event(
            ctx,
            event,
            button_msg,
            &mut self.loader,
            &mut self.pad,
            &mut self.content,
        ) {
            return Some(HoldToConfirmMsg::Confirmed);
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
        self.buttons.paint();
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.pad.area);
        if self.loader.is_animating() {
            self.loader.bounds(sink)
        } else {
            self.content.bounds(sink)
        }
        self.buttons.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for HoldToConfirm<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("HoldToConfirm");
        t.child("content", &self.content);
    }
}

pub struct CancelHold {
    cancel: Option<Child<Button<&'static str>>>,
    hold: Child<Button<&'static str>>,
}

pub enum CancelHoldMsg {
    Cancelled,
    HoldButton(ButtonMsg),
}

impl CancelHold {
    pub fn new(button_style: ButtonStyleSheet) -> FixedHeightBar<Self> {
        theme::button_bar(Self {
            cancel: Some(Button::with_icon(theme::ICON_CANCEL).into_child()),
            hold: Button::with_text("HOLD TO CONFIRM")
                .styled(button_style)
                .into_child(),
        })
    }

    pub fn with_cancel_arrow() -> FixedHeightBar<Self> {
        theme::button_bar(Self {
            cancel: Some(Button::with_icon(theme::ICON_UP).into_child()),
            hold: Button::with_text("HOLD TO CONFIRM")
                .styled(theme::button_confirm())
                .into_child(),
        })
    }

    pub fn without_cancel() -> FixedHeightBar<Self> {
        theme::button_bar(Self {
            cancel: None,
            hold: Button::with_text("HOLD TO CONFIRM")
                .styled(theme::button_confirm())
                .into_child(),
        })
    }
}

impl Component for CancelHold {
    type Msg = CancelHoldMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        if self.cancel.is_some() {
            let grid = Grid::new(bounds, 1, 4).with_spacing(theme::BUTTON_SPACING);
            self.cancel.place(grid.row_col(0, 0));
            self.hold
                .place(grid.row_col(0, 1).union(grid.row_col(0, 3)));
        } else {
            self.hold.place(bounds);
        };
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(ButtonMsg::Clicked) = self.cancel.event(ctx, event) {
            return Some(CancelHoldMsg::Cancelled);
        }
        self.hold.event(ctx, event).map(CancelHoldMsg::HoldButton)
    }

    fn paint(&mut self) {
        self.cancel.paint();
        self.hold.paint();
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.cancel.bounds(sink);
        self.hold.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for CancelHold {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("CancelHold");
    }
}

/// Hold-to-confirm logic to be called from event handler of the component that
/// owns `pad`, `loader`, and `content` and a Button. It is expected that the
/// associated button already processed `event` and returned `button_msg`.
/// Returns `true` when the interaction successfully finished.
#[must_use]
pub fn handle_hold_event<T>(
    ctx: &mut EventCtx,
    event: Event,
    button_msg: Option<ButtonMsg>,
    loader: &mut Loader,
    pad: &mut Pad,
    content: &mut T,
) -> bool
where
    T: Component,
{
    let now = Instant::now();

    if let Some(LoaderMsg::ShrunkCompletely) = loader.event(ctx, event) {
        // Clear the remnants of the loader.
        pad.clear();
        // Switch it to the initial state, so we stop painting it.
        loader.reset();
        // Re-draw the whole content tree.
        content.request_complete_repaint(ctx);
        // This can be a result of an animation frame event, we should take
        // care to not short-circuit here and deliver the event to the
        // content as well.
    }
    match button_msg {
        Some(ButtonMsg::Pressed) => {
            loader.start_growing(ctx, now);
            pad.clear(); // Clear the remnants of the content.
        }
        Some(ButtonMsg::Released) => {
            loader.start_shrinking(ctx, now);
        }
        Some(ButtonMsg::Clicked) => {
            if loader.is_completely_grown(now) || animation_disabled() {
                return true;
            } else {
                loader.start_shrinking(ctx, now);
            }
        }
        _ => {}
    }

    false
}
