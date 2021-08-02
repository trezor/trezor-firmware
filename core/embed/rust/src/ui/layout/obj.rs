use core::{
    cell::RefCell,
    convert::{TryFrom, TryInto},
    time::Duration,
};

use crate::{
    error::Error,
    micropython::{
        gc::Gc,
        map::Map,
        obj::{Obj, ObjBase},
        qstr::Qstr,
        typ::Type,
    },
    ui::component::{model::HidEvent, Child, Component, Event, EventCtx, Never, TimerToken},
    util,
};

/// Conversion trait implemented by components that know how to convert their
/// message values into MicroPython `Obj`s. We can automatically implement
/// `ComponentMsgObj` for components whose message types implement `TryInto`.
pub trait ComponentMsgObj: Component {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error>;
}

impl<T> ComponentMsgObj for T
where
    T: Component,
    T::Msg: TryInto<Obj, Error = Error>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        msg.try_into()
    }
}

/// In order to store any type of component in a layout, we need to access it
/// through an object-safe trait. `Component` itself is not object-safe because
/// of `Component::Msg` associated type. `ObjComponent` is a simple object-safe
/// wrapping trait that is implemented for all components where `Component::Msg`
/// can be converted to `Obj` through the `ComponentMsgObj` trait.
pub trait ObjComponent {
    fn obj_event(&mut self, ctx: &mut EventCtx, event: Event) -> Result<Obj, Error>;
    fn obj_paint(&mut self);
}

impl<T> ObjComponent for Child<T>
where
    T: ComponentMsgObj,
{
    fn obj_event(&mut self, ctx: &mut EventCtx, event: Event) -> Result<Obj, Error> {
        if let Some(msg) = self.event(ctx, event) {
            self.inner().msg_try_into_obj(msg)
        } else {
            Ok(Obj::const_none())
        }
    }

    fn obj_paint(&mut self) {
        self.paint();
    }
}

#[cfg(feature = "ui_debug")]
mod maybe_trace {
    pub trait ObjComponentTrace: super::ObjComponent + crate::trace::Trace {}
    impl<T> ObjComponentTrace for T where T: super::ObjComponent + crate::trace::Trace {}
}

#[cfg(not(feature = "ui_debug"))]
mod maybe_trace {
    pub trait ObjComponentTrace: super::ObjComponent {}
    impl<T> ObjComponentTrace for T where T: super::ObjComponent {}
}

/// Trait that combines `ObjComponent` with `Trace` if `ui_debug` is enabled,
/// and pure `ObjComponent` otherwise.
use maybe_trace::ObjComponentTrace;

/// `LayoutObj` is a GC-allocated object exported to MicroPython, with type
/// `LayoutObj::obj_type()`. It wraps a root component through the
/// `ObjComponent` trait.
#[repr(C)]
pub struct LayoutObj {
    base: ObjBase,
    inner: RefCell<LayoutObjInner>,
}

struct LayoutObjInner {
    root: Gc<dyn ObjComponentTrace>,
    event_ctx: EventCtx,
    timer_fn: Obj,
}

impl LayoutObj {
    /// Create a new `LayoutObj`, wrapping a root component.
    pub fn new(root: impl ObjComponentTrace + 'static) -> Result<Gc<Self>, Error> {
        // SAFETY: We are coercing GC-allocated sized ptr into an unsized one.
        let root =
            unsafe { Gc::from_raw(Gc::into_raw(Gc::new(root)?) as *mut dyn ObjComponentTrace) };

        Gc::new(Self {
            base: Self::obj_type().as_base(),
            inner: RefCell::new(LayoutObjInner {
                root,
                event_ctx: EventCtx::new(),
                timer_fn: Obj::const_none(),
            }),
        })
    }

    /// Timer callback is expected to be a callable object of the following
    /// form: `def timer(token: int, deadline_in_ms: int)`.
    fn obj_set_timer_fn(&self, timer_fn: Obj) {
        self.inner.borrow_mut().timer_fn = timer_fn;
    }

    /// Run an event pass over the component tree. After the traversal, any
    /// pending timers are drained into `self.timer_callback`. Returns `Err`
    /// in case the timer callback raises or one of the components returns
    /// an error, `Ok` with the message otherwise.
    fn obj_event(&self, event: Event) -> Result<Obj, Error> {
        let inner = &mut *self.inner.borrow_mut();

        // Clear the upwards-propagating paint request flag from the last event pass.
        inner.event_ctx.clear_paint_requests();

        // Send the event down the component tree. Bail out in case of failure.
        // SAFETY: `inner.root` is unique because of the `inner.borrow_mut()`.
        let msg = unsafe { Gc::as_mut(&mut inner.root) }.obj_event(&mut inner.event_ctx, event)?;

        // All concerning `Child` wrappers should have already marked themselves for
        // painting by now, and we're prepared for a paint pass.

        // Drain any pending timers into the callback.
        while let Some((token, deadline)) = inner.event_ctx.pop_timer() {
            let token = token.try_into();
            let deadline = deadline.try_into();
            if let (Ok(token), Ok(deadline)) = (token, deadline) {
                inner.timer_fn.call_with_n_args(&[token, deadline])?;
            } else {
                // Failed to convert token or deadline into `Obj`, skip.
            }
        }

        Ok(msg)
    }

    /// Run a paint pass over the component tree.
    fn obj_paint_if_requested(&self) {
        let mut inner = self.inner.borrow_mut();
        // SAFETY: `inner.root` is unique because of the `inner.borrow_mut()`.
        unsafe { Gc::as_mut(&mut inner.root) }.obj_paint();
    }

    /// Run a tracing pass over the component tree. Passed `callback` is called
    /// with each piece of tracing information. Panics in case the callback
    /// raises an exception.
    #[cfg(feature = "ui_debug")]
    fn obj_trace(&self, callback: Obj) {
        use crate::trace::{Trace, Tracer};

        struct CallbackTracer(Obj);

        impl Tracer for CallbackTracer {
            fn bytes(&mut self, b: &[u8]) {
                self.0.call_with_n_args(&[b.try_into().unwrap()]).unwrap();
            }

            fn string(&mut self, s: &str) {
                self.0.call_with_n_args(&[s.try_into().unwrap()]).unwrap();
            }

            fn symbol(&mut self, name: &str) {
                self.0
                    .call_with_n_args(&[name.try_into().unwrap()])
                    .unwrap();
            }

            fn open(&mut self, name: &str) {
                self.0
                    .call_with_n_args(&[name.try_into().unwrap()])
                    .unwrap();
            }

            fn field(&mut self, name: &str, value: &dyn Trace) {
                self.0
                    .call_with_n_args(&[name.try_into().unwrap()])
                    .unwrap();
                value.trace(self);
            }

            fn close(&mut self) {}
        }

        self.inner
            .borrow()
            .root
            .trace(&mut CallbackTracer(callback));
    }

    fn obj_type() -> &'static Type {
        static TYPE: Type = obj_type! {
            name: Qstr::MP_QSTR_Layout,
            locals: &obj_dict!(obj_map! {
                Qstr::MP_QSTR_set_timer_fn => obj_fn_2!(ui_layout_set_timer_fn).as_obj(),
                Qstr::MP_QSTR_hid_event => obj_fn_var!(4, 4, ui_layout_hid_event).as_obj(),
                Qstr::MP_QSTR_timer => obj_fn_2!(ui_layout_timer).as_obj(),
                Qstr::MP_QSTR_paint => obj_fn_1!(ui_layout_paint).as_obj(),
                Qstr::MP_QSTR_trace => obj_fn_2!(ui_layout_trace).as_obj(),
            }),
        };
        &TYPE
    }
}

impl From<Gc<LayoutObj>> for Obj {
    fn from(val: Gc<LayoutObj>) -> Self {
        // SAFETY:
        //  - We are GC-allocated.
        //  - We are `repr(C)`.
        //  - We have a `base` as the first field with the correct type.
        unsafe { Obj::from_ptr(Gc::into_raw(val).cast()) }
    }
}

impl TryFrom<Obj> for Gc<LayoutObj> {
    type Error = Error;

    fn try_from(value: Obj) -> Result<Self, Self::Error> {
        if LayoutObj::obj_type().is_type_of(value) {
            // SAFETY: We assume that if `value` is an object pointer with the correct type,
            // it is always GC-allocated.
            let this = unsafe { Gc::from_raw(value.as_ptr().cast()) };
            Ok(this)
        } else {
            Err(Error::TypeError)
        }
    }
}

impl TryFrom<Obj> for TimerToken {
    type Error = Error;

    fn try_from(value: Obj) -> Result<Self, Self::Error> {
        let raw: usize = value.try_into()?;
        let this = Self::from_raw(raw);
        Ok(this)
    }
}

impl TryFrom<TimerToken> for Obj {
    type Error = Error;

    fn try_from(value: TimerToken) -> Result<Self, Self::Error> {
        value.into_raw().try_into()
    }
}

impl TryFrom<Duration> for Obj {
    type Error = Error;

    fn try_from(value: Duration) -> Result<Self, Self::Error> {
        let millis: usize = value.as_millis().try_into()?;
        millis.try_into()
    }
}

impl From<Never> for Obj {
    fn from(_: Never) -> Self {
        unreachable!()
    }
}

extern "C" fn ui_layout_set_timer_fn(this: Obj, timer_fn: Obj) -> Obj {
    let block = || {
        let this: Gc<LayoutObj> = this.try_into()?;
        this.obj_set_timer_fn(timer_fn);
        Ok(Obj::const_true())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn ui_layout_hid_event(n_args: usize, args: *const Obj) -> Obj {
    let block = |args: &[Obj], _kwargs: &Map| {
        if args.len() != 4 {
            return Err(Error::TypeError);
        }
        let this: Gc<LayoutObj> = args[0].try_into()?;
        let event = HidEvent::new(
            args[1].try_into()?,
            args[2].try_into()?,
            args[3].try_into()?,
        )?;
        let msg = this.obj_event(Event::HumanInput(event))?;
        Ok(msg)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, &Map::EMPTY, block) }
}

extern "C" fn ui_layout_timer(this: Obj, token: Obj) -> Obj {
    let block = || {
        let this: Gc<LayoutObj> = this.try_into()?;
        let event = Event::Timer(token.try_into()?);
        let msg = this.obj_event(event)?;
        Ok(msg)
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn ui_layout_paint(this: Obj) -> Obj {
    let block = || {
        let this: Gc<LayoutObj> = this.try_into()?;
        this.obj_paint_if_requested();
        Ok(Obj::const_true())
    };
    unsafe { util::try_or_raise(block) }
}

#[cfg(feature = "ui_debug")]
#[no_mangle]
pub extern "C" fn ui_debug_layout_type() -> &'static Type {
    LayoutObj::obj_type()
}

#[cfg(feature = "ui_debug")]
extern "C" fn ui_layout_trace(this: Obj, callback: Obj) -> Obj {
    let block = || {
        let this: Gc<LayoutObj> = this.try_into()?;
        this.obj_trace(callback);
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

#[cfg(not(feature = "ui_debug"))]
extern "C" fn ui_layout_trace(_this: Obj, _callback: Obj) -> Obj {
    Obj::const_none()
}
