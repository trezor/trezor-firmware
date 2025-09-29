use crate::ui::{
    component::{Component, Event, EventCtx},
    event::BLEEvent,
    geometry::Rect,
    shape::Renderer,
};

pub enum BLEHandlerMode {
    /// Advertising without whitelist started, waiting for some host to respond
    WaitingForPairingRequest,
    /// Pairing in progress, Trezor needs to allow/reject
    WaitingForPairingCancel,
    /// Pairing in progress, allowed from Trezor side, waiting for BLE module to
    /// confirm success
    WaitingForPairingCompletion,
}

pub struct BLEHandler<T> {
    inner: T,
    state: BLEHandlerMode,
}

pub enum BLEHandlerMsg<TMsg> {
    Content(TMsg),
    PairingCode(u32),
    PairingCompleted,
    Cancelled,
}

impl<T> BLEHandler<T> {
    pub fn new(inner: T, state: BLEHandlerMode) -> Self {
        Self { inner, state }
    }
}

impl<T> Component for BLEHandler<T>
where
    T: Component,
{
    type Msg = BLEHandlerMsg<T::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.inner.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match (event, &self.state) {
            (
                Event::BLE(BLEEvent::PairingRequest(num)),
                BLEHandlerMode::WaitingForPairingRequest,
            ) => return Some(BLEHandlerMsg::PairingCode(num)),
            (
                Event::BLE(BLEEvent::PairingCompleted),
                BLEHandlerMode::WaitingForPairingCompletion,
            ) => return Some(BLEHandlerMsg::PairingCompleted),
            (
                Event::BLE(
                    BLEEvent::PairingCanceled | BLEEvent::Disconnected | BLEEvent::PairingNotNeeded,
                ),
                _,
            ) => return Some(BLEHandlerMsg::Cancelled),
            _ => {}
        }
        self.inner.event(ctx, event).map(BLEHandlerMsg::Content)
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.inner.render(target)
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for BLEHandler<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.inner.trace(t)
    }
}

#[cfg(feature = "micropython")]
mod micropython {
    use super::*;
    use crate::{
        error::Error,
        micropython::obj::Obj,
        ui::layout::{
            obj::ComponentMsgObj,
            result::{CANCELLED, CONFIRMED},
        },
    };
    impl<T> ComponentMsgObj for BLEHandler<T>
    where
        T: ComponentMsgObj,
    {
        fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
            match msg {
                BLEHandlerMsg::Content(msg) => self.inner.msg_try_into_obj(msg),
                BLEHandlerMsg::PairingCode(num) => num.try_into(),
                BLEHandlerMsg::Cancelled => Ok(CANCELLED.as_obj()),
                BLEHandlerMsg::PairingCompleted => Ok(CONFIRMED.as_obj()),
            }
        }
    }
}
