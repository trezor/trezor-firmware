use core::{
    cell::RefCell,
    convert::{TryFrom, TryInto},
    lazy::Lazy,
    time::Duration,
};

use crate::{
    error::Error,
    micropython::{
        dict::Dict,
        func::Func,
        gc::Gc,
        map::{Map, MapElem},
        obj::{Obj, ObjBase},
        qstr::Qstr,
        typ::Type,
    },
    ui::{
        component::{Component, Event, EventCtx, TimerToken},
        math::Point,
    },
};

/// In order to store any type of component in a layout, we need to access it
/// through an object-safe trait. `Component` itself is not object-safe because
/// of `Component::Msg` associated type. `ObjComponent` is a simple object-safe
/// wrapping trait that is implemented for all components where `Component::Msg`
/// can be converted to `Obj`.
pub trait ObjComponent {
    fn obj_event(&mut self, ctx: &mut EventCtx, event: Event) -> Obj;
    fn obj_paint_if_requested(&mut self);
}

impl<T> ObjComponent for T
where
    T: Component,
    T::Msg: Into<Obj>,
{
    fn obj_event(&mut self, ctx: &mut EventCtx, event: Event) -> Obj {
        self.event(ctx, event)
            .map_or_else(Obj::const_none, Into::into)
    }

    fn obj_paint_if_requested(&mut self) {
        self.paint_if_requested();
    }
}

/// `LayoutObj` is a GC-allocated object export to MicroPython, with type
/// `LayoutObj::obj_type()`. It wraps a root component through the
/// `ObjComponent` trait.
#[repr(C)]
pub struct LayoutObj {
    base: ObjBase,
    timer_callback: Obj,
    event_ctx: RefCell<EventCtx>,
    root: Gc<RefCell<dyn ObjComponent>>,
}

impl LayoutObj {
    /// Create a new `LayoutObj` with a root component and a `timer_callback`.
    /// Timer callback is expected to be a callable object of the following
    /// form: `def timer(token: int, deadline_in_ms: int)`.
    pub fn new(root: impl ObjComponent + 'static, timer_callback: Obj) -> Gc<Self> {
        Gc::new(Self {
            base: Self::obj_type().in_base(),
            timer_callback,
            event_ctx: RefCell::new(EventCtx::new()),
            root: Gc::new(RefCell::new(root)),
        })
    }

    /// Run an event pass over the component tree. After the traversal, any
    /// pending timers are drained into `self.timer_callback`.
    fn obj_event(&self, event: Event) -> Obj {
        let mut event_ctx = self.event_ctx.borrow_mut();
        let mut root = self.root.borrow_mut();

        let msg = root.obj_event(&mut event_ctx, event);

        // Drain any pending timers into the callback.
        while let Some((token, deadline)) = event_ctx.pop_timer() {
            let token = token.try_into();
            let deadline = deadline.try_into();
            match (token, deadline) {
                (Ok(token), Ok(deadline)) => {
                    self.timer_callback.call_with_n_args(&[token, deadline]);
                }
                _ => {
                    // Failed to convert token or deadline into `Obj`, skip.
                }
            }
        }

        msg
    }

    /// Run a paint pass over the component tree.
    fn obj_paint_if_requested(&self) {
        self.root.borrow_mut().obj_paint_if_requested();
    }

    fn obj_type() -> &'static Type {
        // TODO: Remove `Lazy`, generate with a macro into `static`, not `static mut`.
        static mut TOUCH_START: Lazy<Func> = Lazy::new(|| Func::extern_3(ui_layout_touch_start));
        static mut TOUCH_MOVE: Lazy<Func> = Lazy::new(|| Func::extern_3(ui_layout_touch_move));
        static mut TOUCH_END: Lazy<Func> = Lazy::new(|| Func::extern_3(ui_layout_touch_end));
        static mut TIMER: Lazy<Func> = Lazy::new(|| Func::extern_2(ui_layout_timer));
        static mut PAINT: Lazy<Func> = Lazy::new(|| Func::extern_1(ui_layout_paint));
        static mut TABLE: Lazy<[MapElem; 5]> = Lazy::new(|| {
            [
                Map::at(Qstr::MP_QSTR_touch_start, unsafe { TOUCH_START.to_obj() }),
                Map::at(Qstr::MP_QSTR_touch_move, unsafe { TOUCH_MOVE.to_obj() }),
                Map::at(Qstr::MP_QSTR_touch_end, unsafe { TOUCH_END.to_obj() }),
                Map::at(Qstr::MP_QSTR_timer, unsafe { TIMER.to_obj() }),
                Map::at(Qstr::MP_QSTR_paint, unsafe { PAINT.to_obj() }),
            ]
        });
        static mut DICT: Lazy<Dict> = Lazy::new(|| Dict::new(Map::fixed(unsafe { &TABLE })));
        static mut TYPE: Lazy<Type> = Lazy::new(|| {
            Type::new()
                .with_name(Qstr::MP_QSTR_Layout)
                .with_locals(unsafe { &DICT })
        });
        Lazy::force(unsafe { &TYPE })
    }
}

impl Into<Obj> for Gc<LayoutObj> {
    fn into(self) -> Obj {
        // SAFETY:
        //  - We are GC-allocated.
        //  - We are `repr(C)`.
        //  - We have a `base` as the first field with the correct type.
        unsafe { Obj::from_ptr(Self::into_raw(self).cast()) }
    }
}

impl TryFrom<Obj> for Gc<LayoutObj> {
    type Error = Error;

    fn try_from(value: Obj) -> Result<Self, Self::Error> {
        if LayoutObj::obj_type().is_type_of(value) {
            // SAFETY: We assume that if `value` is an object pointer with the correct type,
            // it always is GC-allocated.
            let this = unsafe { Gc::from_raw(value.as_ptr().cast()) };
            Ok(this)
        } else {
            Err(Error::InvalidType)
        }
    }
}

impl TryFrom<Obj> for TimerToken {
    type Error = Error;

    fn try_from(value: Obj) -> Result<Self, Self::Error> {
        let raw = value.try_into()?;
        let this = Self::from_raw(raw);
        Ok(this)
    }
}

impl TryInto<Obj> for TimerToken {
    type Error = Error;

    fn try_into(self) -> Result<Obj, Self::Error> {
        self.into_raw().try_into()
    }
}

impl TryInto<Obj> for Duration {
    type Error = Error;

    fn try_into(self) -> Result<Obj, Self::Error> {
        let int: usize = self.as_millis().try_into()?;
        int.try_into()
    }
}

fn try_or_none(f: impl FnOnce() -> Result<Obj, Error>) -> Obj {
    f().unwrap_or(Obj::const_none())
}

extern "C" fn ui_layout_touch_start(this: Obj, x: Obj, y: Obj) -> Obj {
    try_or_none(|| {
        let this: Gc<LayoutObj> = this.try_into()?;
        let event = Event::TouchStart(Point::new(x.try_into()?, y.try_into()?));
        let msg = this.obj_event(event);
        Ok(msg)
    })
}

extern "C" fn ui_layout_touch_move(this: Obj, x: Obj, y: Obj) -> Obj {
    try_or_none(|| {
        let this: Gc<LayoutObj> = this.try_into()?;
        let event = Event::TouchMove(Point::new(x.try_into()?, y.try_into()?));
        let msg = this.obj_event(event);
        Ok(msg)
    })
}

extern "C" fn ui_layout_touch_end(this: Obj, x: Obj, y: Obj) -> Obj {
    try_or_none(|| {
        let this: Gc<LayoutObj> = this.try_into()?;
        let event = Event::TouchEnd(Point::new(x.try_into()?, y.try_into()?));
        let msg = this.obj_event(event);
        Ok(msg)
    })
}

extern "C" fn ui_layout_timer(this: Obj, token: Obj) -> Obj {
    try_or_none(|| {
        let this: Gc<LayoutObj> = this.try_into()?;
        let event = Event::Timer(token.try_into()?);
        let msg = this.obj_event(event);
        Ok(msg)
    })
}

extern "C" fn ui_layout_paint(this: Obj) -> Obj {
    try_or_none(|| {
        let this: Gc<LayoutObj> = this.try_into()?;
        this.obj_paint_if_requested();
        Ok(Obj::const_none())
    })
}
