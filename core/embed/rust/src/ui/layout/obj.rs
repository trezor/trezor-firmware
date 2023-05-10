use core::{
    cell::RefCell,
    convert::{TryFrom, TryInto},
};

use crate::{
    error::Error,
    maybe_trace::MaybeTrace,
    micropython::{
        buffer::StrBuffer,
        gc::Gc,
        map::Map,
        obj::{Obj, ObjBase},
        qstr::Qstr,
        typ::Type,
        util,
    },
    time::Duration,
    ui::{
        component::{Child, Component, Event, EventCtx, Never, TimerToken},
        constant,
        display::sync,
        geometry::Rect,
    },
};

#[cfg(feature = "button")]
use crate::ui::event::ButtonEvent;
#[cfg(feature = "touch")]
use crate::ui::event::TouchEvent;
use crate::ui::event::USBEvent;

/// Conversion trait implemented by components that know how to convert their
/// message values into MicroPython `Obj`s.
pub trait ComponentMsgObj: Component {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error>;
}

/// Object-safe interface between trait `Component` and MicroPython world. It
/// converts the result of `Component::event` into `Obj` via the
/// `ComponentMsgObj` trait, in order to easily return the value to Python. It
/// also optionally implies `Trace` for UI debugging.
/// Note: we need to use an object-safe trait in order to store it in a `Gc<dyn
/// T>` field. `Component` itself is not object-safe because of `Component::Msg`
/// associated type.
pub trait ObjComponent: MaybeTrace {
    fn obj_place(&mut self, bounds: Rect) -> Rect;
    fn obj_event(&mut self, ctx: &mut EventCtx, event: Event) -> Result<Obj, Error>;
    fn obj_paint(&mut self) -> bool;
    fn obj_bounds(&self, _sink: &mut dyn FnMut(Rect)) {}
    fn obj_skip_paint(&mut self) {}
}

impl<T> ObjComponent for Child<T>
where
    T: ComponentMsgObj + MaybeTrace,
{
    fn obj_place(&mut self, bounds: Rect) -> Rect {
        self.place(bounds)
    }

    fn obj_event(&mut self, ctx: &mut EventCtx, event: Event) -> Result<Obj, Error> {
        if let Some(msg) = self.event(ctx, event) {
            self.inner().msg_try_into_obj(msg)
        } else {
            Ok(Obj::const_none())
        }
    }

    fn obj_paint(&mut self) -> bool {
        let will_paint = self.will_paint();
        self.paint();
        will_paint
    }

    #[cfg(feature = "ui_bounds")]
    fn obj_bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.bounds(sink)
    }

    fn obj_skip_paint(&mut self) {
        self.skip_paint()
    }
}

/// `LayoutObj` is a GC-allocated object exported to MicroPython, with type
/// `LayoutObj::obj_type()`. It wraps a root component through the
/// `ObjComponent` trait.
#[repr(C)]
pub struct LayoutObj {
    base: ObjBase,
    inner: RefCell<LayoutObjInner>,
}

struct LayoutObjInner {
    root: Gc<dyn ObjComponent>,
    event_ctx: EventCtx,
    timer_fn: Obj,
    page_count: u16,
}

impl LayoutObj {
    /// Create a new `LayoutObj`, wrapping a root component.
    pub fn new(root: impl ComponentMsgObj + MaybeTrace + 'static) -> Result<Gc<Self>, Error> {
        // Let's wrap the root component into a `Child` to maintain the top-level
        // invalidation logic.
        let wrapped_root = Child::new(root);
        // SAFETY: We are coercing GC-allocated sized ptr into an unsized one.
        let root =
            unsafe { Gc::from_raw(Gc::into_raw(Gc::new(wrapped_root)?) as *mut dyn ObjComponent) };

        Gc::new(Self {
            base: Self::obj_type().as_base(),
            inner: RefCell::new(LayoutObjInner {
                root,
                event_ctx: EventCtx::new(),
                timer_fn: Obj::const_none(),
                page_count: 1,
            }),
        })
    }

    pub fn skip_first_paint(&self) {
        let mut inner = self.inner.borrow_mut();

        // SAFETY: `inner.root` is unique because of the `inner.borrow_mut()`.
        unsafe { Gc::as_mut(&mut inner.root) }.obj_skip_paint();
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

        // Place the root component on the screen in case it was previously requested.
        if inner.event_ctx.needs_place_before_next_event_or_paint() {
            // SAFETY: `inner.root` is unique because of the `inner.borrow_mut()`.
            unsafe { Gc::as_mut(&mut inner.root) }.obj_place(constant::screen());
        }

        // Clear the leftover flags from the previous event pass.
        inner.event_ctx.clear();

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

        if let Some(count) = inner.event_ctx.page_count() {
            inner.page_count = count as u16;
        }

        Ok(msg)
    }

    /// Run a paint pass over the component tree. Returns true if any component
    /// actually requested painting since last invocation of the function.
    fn obj_paint_if_requested(&self) -> bool {
        let mut inner = self.inner.borrow_mut();

        // Place the root component on the screen in case it was previously requested.
        if inner.event_ctx.needs_place_before_next_event_or_paint() {
            // SAFETY: `inner.root` is unique because of the `inner.borrow_mut()`.
            unsafe { Gc::as_mut(&mut inner.root) }.obj_place(constant::screen());
        }

        sync();

        // SAFETY: `inner.root` is unique because of the `inner.borrow_mut()`.
        unsafe { Gc::as_mut(&mut inner.root) }.obj_paint()
    }

    /// Run a tracing pass over the component tree. Passed `callback` is called
    /// with each piece of tracing information. Panics in case the callback
    /// raises an exception.
    #[cfg(feature = "ui_debug")]
    fn obj_trace(&self, callback: Obj) {
        use crate::trace::JsonTracer;

        let mut tracer = JsonTracer::new(|text: &str| {
            unwrap!(callback.call_with_n_args(&[unwrap!(text.try_into())]));
        });

        // For Reasons(tm), we must pass a closure in which we call `root.trace(t)`,
        // instead of passing `root` into the tracer.

        // (The Reasons being, root is a `Gc<dyn ObjComponent>`, and `Gc` does not
        // implement `Trace`, and `dyn ObjComponent` is unsized so we can't deref it to
        // claim that it implements `Trace`, and we also can't upcast it to `&dyn Trace`
        // because trait upcasting is unstable.
        // Luckily, calling `root.trace()` works perfectly fine in spite of the above.)
        tracer.root(&|t| {
            self.inner.borrow().root.trace(t);
        });
    }

    fn obj_page_count(&self) -> Obj {
        self.inner.borrow().page_count.into()
    }

    #[cfg(feature = "ui_debug")]
    fn obj_bounds(&self) {
        use crate::ui::display;

        // Sink for `Trace::bounds` that draws the boundaries using pseudorandom color.
        fn wireframe(r: Rect) {
            let w = r.width() as u16;
            let h = r.height() as u16;
            let color = display::Color::from_u16(w.rotate_right(w.into()).wrapping_add(h * 8));
            display::rect_stroke(r, color)
        }

        // use crate::ui::model_tt::theme;
        // wireframe(theme::borders());
        self.inner.borrow().root.obj_bounds(&mut wireframe);
    }

    fn obj_type() -> &'static Type {
        static TYPE: Type = obj_type! {
            name: Qstr::MP_QSTR_Layout,
            locals: &obj_dict!(obj_map! {
                Qstr::MP_QSTR_attach_timer_fn => obj_fn_2!(ui_layout_attach_timer_fn).as_obj(),
                Qstr::MP_QSTR_touch_event => obj_fn_var!(4, 4, ui_layout_touch_event).as_obj(),
                Qstr::MP_QSTR_button_event => obj_fn_var!(3, 3, ui_layout_button_event).as_obj(),
                Qstr::MP_QSTR_progress_event => obj_fn_var!(3, 3, ui_layout_progress_event).as_obj(),
                Qstr::MP_QSTR_usb_event => obj_fn_var!(2, 2, ui_layout_usb_event).as_obj(),
                Qstr::MP_QSTR_timer => obj_fn_2!(ui_layout_timer).as_obj(),
                Qstr::MP_QSTR_paint => obj_fn_1!(ui_layout_paint).as_obj(),
                Qstr::MP_QSTR_request_complete_repaint => obj_fn_1!(ui_layout_request_complete_repaint).as_obj(),
                Qstr::MP_QSTR_trace => obj_fn_2!(ui_layout_trace).as_obj(),
                Qstr::MP_QSTR_bounds => obj_fn_1!(ui_layout_bounds).as_obj(),
                Qstr::MP_QSTR_page_count => obj_fn_1!(ui_layout_page_count).as_obj(),
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
        let raw: u32 = value.try_into()?;
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
        let millis: usize = value.to_millis().try_into()?;
        millis.try_into()
    }
}

impl TryFrom<Never> for Obj {
    type Error = Error;

    fn try_from(_: Never) -> Result<Self, Self::Error> {
        unreachable!()
    }
}

extern "C" fn ui_layout_attach_timer_fn(this: Obj, timer_fn: Obj) -> Obj {
    let block = || {
        let this: Gc<LayoutObj> = this.try_into()?;
        this.obj_set_timer_fn(timer_fn);
        let msg = this.obj_event(Event::Attach)?;
        assert!(msg == Obj::const_none());
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

#[cfg(feature = "touch")]
extern "C" fn ui_layout_touch_event(n_args: usize, args: *const Obj) -> Obj {
    let block = |args: &[Obj], _kwargs: &Map| {
        if args.len() != 4 {
            return Err(Error::TypeError);
        }
        let this: Gc<LayoutObj> = args[0].try_into()?;
        let event = TouchEvent::new(
            args[1].try_into()?,
            args[2].try_into()?,
            args[3].try_into()?,
        )?;
        let msg = this.obj_event(Event::Touch(event))?;
        Ok(msg)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, &Map::EMPTY, block) }
}

#[cfg(not(feature = "touch"))]
extern "C" fn ui_layout_touch_event(_n_args: usize, _args: *const Obj) -> Obj {
    Obj::const_none()
}

#[cfg(feature = "button")]
extern "C" fn ui_layout_button_event(n_args: usize, args: *const Obj) -> Obj {
    let block = |args: &[Obj], _kwargs: &Map| {
        if args.len() != 3 {
            return Err(Error::TypeError);
        }
        let this: Gc<LayoutObj> = args[0].try_into()?;
        let event = ButtonEvent::new(args[1].try_into()?, args[2].try_into()?)?;
        let msg = this.obj_event(Event::Button(event))?;
        Ok(msg)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, &Map::EMPTY, block) }
}

#[cfg(not(feature = "button"))]
extern "C" fn ui_layout_button_event(_n_args: usize, _args: *const Obj) -> Obj {
    Obj::const_none()
}

extern "C" fn ui_layout_progress_event(n_args: usize, args: *const Obj) -> Obj {
    let block = |args: &[Obj], _kwargs: &Map| {
        if args.len() != 3 {
            return Err(Error::TypeError);
        }
        let this: Gc<LayoutObj> = args[0].try_into()?;
        let value: u16 = args[1].try_into()?;
        let description: StrBuffer = args[2].try_into()?;
        let msg = this.obj_event(Event::Progress(value, description.as_ref()))?;
        Ok(msg)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, &Map::EMPTY, block) }
}

extern "C" fn ui_layout_usb_event(n_args: usize, args: *const Obj) -> Obj {
    let block = |args: &[Obj], _kwargs: &Map| {
        if args.len() != 2 {
            return Err(Error::TypeError);
        }
        let this: Gc<LayoutObj> = args[0].try_into()?;
        let event = USBEvent::Connected(args[1].try_into()?);
        let msg = this.obj_event(Event::USB(event))?;
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
        let painted = this.obj_paint_if_requested().into();
        Ok(painted)
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn ui_layout_request_complete_repaint(this: Obj) -> Obj {
    let block = || {
        let this: Gc<LayoutObj> = this.try_into()?;
        let event = Event::RequestPaint;
        let msg = this.obj_event(event)?;
        if msg != Obj::const_none() {
            // Messages raised during a `RequestPaint` dispatch are not propagated, let's
            // make sure we don't do that.
            #[cfg(feature = "ui_debug")]
            panic!("cannot raise messages during RequestPaint");
        };
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn ui_layout_page_count(this: Obj) -> Obj {
    let block = || {
        let this: Gc<LayoutObj> = this.try_into()?;
        Ok(this.obj_page_count())
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

#[cfg(feature = "ui_bounds")]
extern "C" fn ui_layout_bounds(this: Obj) -> Obj {
    let block = || {
        let this: Gc<LayoutObj> = this.try_into()?;
        this.obj_bounds();
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

#[cfg(not(feature = "ui_bounds"))]
extern "C" fn ui_layout_bounds(_this: Obj) -> Obj {
    Obj::const_none()
}
