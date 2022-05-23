use crate::{
    time::Instant,
    ui::{
        component::{Child, Component, ComponentExt, Event, EventCtx, Pad},
        geometry::{Grid, Rect},
        model_tt::component::DialogLayout,
    },
};

use super::{theme, Button, ButtonMsg, Loader, LoaderMsg};

pub enum HoldToConfirmMsg<T> {
    Content(T),
    Confirmed,
    Cancelled,
}

pub struct HoldToConfirm<T> {
    loader: Loader,
    content: Child<T>,
    buttons: CancelHold,
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
            buttons: CancelHold::new(),
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
        let layout = DialogLayout::middle(bounds);
        self.pad.place(layout.content);
        self.loader.place(layout.content);
        self.content.place(layout.content);
        self.buttons.place(layout.controls);
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
    fn trace(&self, d: &mut dyn crate::trace::Tracer) {
        d.open("HoldToConfirm");
        self.content.trace(d);
        d.close();
    }
}

pub struct CancelHold {
    cancel: Button<&'static str>,
    hold: Button<&'static str>,
}

pub enum CancelHoldMsg {
    Cancelled,
    HoldButton(ButtonMsg),
}

impl CancelHold {
    pub fn new() -> Self {
        Self {
            cancel: Button::with_icon(theme::ICON_CANCEL),
            hold: Button::with_text("HOLD TO CONFIRM").styled(theme::button_confirm()),
        }
    }
}

impl Component for CancelHold {
    type Msg = CancelHoldMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let grid = Grid::new(bounds, 1, 4).with_spacing(theme::BUTTON_SPACING);
        self.cancel.place(grid.row_col(0, 0));
        self.hold
            .place(grid.row_col(0, 1).union(grid.row_col(0, 3)));
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

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.cancel.bounds(sink);
        self.hold.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for CancelHold {
    fn trace(&self, d: &mut dyn crate::trace::Tracer) {
        d.string("CancelHold")
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
            if loader.is_completely_grown(now) {
                loader.reset();
                return true;
            } else {
                loader.start_shrinking(ctx, now);
            }
        }
        _ => {}
    }

    false
}
