use core::{
    cell::{RefCell, RefMut},
    convert::{TryFrom, TryInto},
    ops::{Deref, DerefMut},
};
use num_traits::{FromPrimitive, ToPrimitive};

#[cfg(feature = "button")]
use crate::ui::event::ButtonEvent;
#[cfg(feature = "new_rendering")]
use crate::ui::{display::Color, shape::render_on_display};
#[cfg(feature = "touch")]
use crate::ui::{event::TouchEvent, geometry::Direction};
use crate::{
    error::Error,
    maybe_trace::MaybeTrace,
    micropython::{
        buffer::StrBuffer,
        gc::{self, Gc, GcBox},
        macros::{obj_dict, obj_fn_1, obj_fn_2, obj_fn_3, obj_fn_var, obj_map, obj_type},
        map::Map,
        obj::{Obj, ObjBase},
        qstr::Qstr,
        simple_type::SimpleTypeObj,
        typ::Type,
        util,
    },
    time::Duration,
    ui::{
        button_request::ButtonRequest,
        component::{base::AttachType, Component, Event, EventCtx, Never, TimerToken},
        constant, display,
        event::USBEvent,
        geometry::Rect,
    },
};

impl AttachType {
    fn to_obj(self) -> Obj {
        match self {
            Self::Initial => Obj::const_none(),
            Self::Resume => 1u8.into(),
            #[cfg(feature = "touch")]
            Self::Swipe(dir) => (2u8 + unwrap!(dir.to_u8())).into(),
        }
    }
    fn try_from_obj(obj: Obj) -> Result<Self, Error> {
        if obj == Obj::const_none() {
            return Ok(Self::Initial);
        }
        let val: u8 = obj.try_into()?;

        match val {
            0 => Ok(Self::Initial),
            1 => Ok(Self::Resume),
            #[cfg(feature = "touch")]
            2..=5 => Ok(Self::Swipe(
                Direction::from_u8(val - 2).ok_or(Error::TypeError)?,
            )),
            _ => Err(Error::TypeError),
        }
    }
}

static ATTACH_TYPE: Type = obj_type! {
    name: Qstr::MP_QSTR_AttachType,
    locals: &obj_dict!(obj_map! {
        Qstr::MP_QSTR_INITIAL => Obj::small_int(0u16),
        Qstr::MP_QSTR_RESUME => Obj::small_int(1u16),
        Qstr::MP_QSTR_SWIPE_UP => Obj::small_int(2u16),
        Qstr::MP_QSTR_SWIPE_DOWN => Obj::small_int(3u16),
        Qstr::MP_QSTR_SWIPE_LEFT => Obj::small_int(4u16),
        Qstr::MP_QSTR_SWIPE_RIGHT => Obj::small_int(5u16),
    }),
};

pub static ATTACH_TYPE_OBJ: SimpleTypeObj = SimpleTypeObj::new(&ATTACH_TYPE);

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
    fn obj_paint(&mut self);
    fn obj_bounds(&self, _sink: &mut dyn FnMut(Rect)) {}
}

impl<T> ObjComponent for T
where
    T: Component + ComponentMsgObj + MaybeTrace,
{
    fn obj_place(&mut self, bounds: Rect) -> Rect {
        self.place(bounds)
    }

    fn obj_event(&mut self, ctx: &mut EventCtx, event: Event) -> Result<Obj, Error> {
        if let Some(msg) = self.event(ctx, event) {
            self.msg_try_into_obj(msg)
        } else {
            Ok(Obj::const_none())
        }
    }

    fn obj_paint(&mut self) {
        #[cfg(not(feature = "new_rendering"))]
        {
            self.paint();
        }

        #[cfg(feature = "new_rendering")]
        {
            render_on_display(None, Some(Color::black()), |target| {
                self.render(target);
            });
        }
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
enum Repaint {
    None,
    Partial,
    Full,
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
    root: Option<GcBox<dyn ObjComponent>>,
    event_ctx: EventCtx,
    timer_fn: Obj,
    page_count: u16,
    repaint: Repaint,
    transition_out: AttachType,
}

impl LayoutObjInner {
    /// Create a new `LayoutObj`, wrapping a root component.
    #[inline(never)]
    pub fn new(root: impl ObjComponent + 'static) -> Result<Self, Error> {
        let root = GcBox::new(root)?;

        Ok(Self {
            root: Some(gc::coerce!(ObjComponent, root)),
            event_ctx: EventCtx::new(),
            timer_fn: Obj::const_none(),
            page_count: 1,
            repaint: Repaint::Full,
            transition_out: AttachType::Initial,
        })
    }

    fn obj_delete(&mut self) {
        self.root = None;
    }

    /// Timer callback is expected to be a callable object of the following
    /// form: `def timer(token: int, duration_ms: int)`.
    fn obj_set_timer_fn(&mut self, timer_fn: Obj) {
        self.timer_fn = timer_fn;
    }

    fn root(&self) -> &impl Deref<Target = dyn ObjComponent> {
        unwrap!(self.root.as_ref())
    }

    fn root_mut(&mut self) -> &mut impl DerefMut<Target = dyn ObjComponent> {
        unwrap!(self.root.as_mut())
    }

    fn obj_request_repaint(&mut self) {
        self.repaint = Repaint::Full;
        let mut dummy_ctx = EventCtx::new();
        let paint_msg = self
            .root_mut()
            .obj_event(&mut dummy_ctx, Event::RequestPaint);
        // paint_msg must not be an error and it must not return a result
        assert!(matches!(paint_msg, Ok(s) if s == Obj::const_none()));
        // there must be no timers set
        assert!(dummy_ctx.pop_timer().is_none());
    }

    /// Run an event pass over the component tree. After the traversal, any
    /// pending timers are drained into `self.timer_callback`. Returns `Err`
    /// in case the timer callback raises or one of the components returns
    /// an error, `Ok` with the message otherwise.
    fn obj_event(&mut self, event: Event) -> Result<Obj, Error> {
        let root = unwrap!(self.root.as_mut());
        // Place the root component on the screen in case it was previously requested.
        if self.event_ctx.needs_place() {
            root.obj_place(constant::screen());
        }

        // Clear the leftover flags from the previous event pass.
        self.event_ctx.clear();

        // Send the event down the component tree. Bail out in case of failure.
        let msg = root.obj_event(&mut self.event_ctx, event)?;

        // Check if we should repaint next time
        if self.event_ctx.needs_repaint_root() {
            self.obj_request_repaint();
        } else if self.event_ctx.needs_repaint() {
            self.repaint = Repaint::Partial;
        }

        // All concerning `Child` wrappers should have already marked themselves for
        // painting by now, and we're prepared for a paint pass.

        // Drain any pending timers into the callback.
        while let Some((token, duration)) = self.event_ctx.pop_timer() {
            let token = token.try_into();
            let duration = duration.try_into();
            if let (Ok(token), Ok(duration)) = (token, duration) {
                self.timer_fn.call_with_n_args(&[token, duration])?;
            } else {
                // Failed to convert token or duration into `Obj`, skip.
            }
        }

        if let Some(count) = self.event_ctx.page_count() {
            self.page_count = count as u16;
        }

        if let Some(t) = self.event_ctx.get_transition_out() {
            self.transition_out = t;
        }

        Ok(msg)
    }

    /// Run a paint pass over the component tree. Returns true if any component
    /// actually requested painting since last invocation of the function.
    fn obj_paint_if_requested(&mut self) -> bool {
        if self.repaint == Repaint::Full {
            display::clear();
        }

        // Place the root component on the screen in case it was previously requested.
        if self.event_ctx.needs_place() {
            self.root_mut().obj_place(constant::screen());
        }

        display::sync();

        if self.repaint != Repaint::None {
            self.repaint = Repaint::None;
            self.root_mut().obj_paint();
            true
        } else {
            false
        }
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
            self.root().trace(t);
        });
    }

    fn obj_page_count(&self) -> Obj {
        self.page_count.into()
    }

    fn obj_button_request(&mut self) -> Result<Obj, Error> {
        match self.event_ctx.button_request() {
            None => Ok(Obj::const_none()),
            Some(ButtonRequest { code, name }) => (code.num().into(), name.try_into()?).try_into(),
        }
    }

    fn obj_get_transition_out(&self) -> Obj {
        self.transition_out.to_obj()
    }
}

impl LayoutObj {
    /// Create a new `LayoutObj`, wrapping a root component.
    pub fn new(root: impl ObjComponent + 'static) -> Result<Gc<Self>, Error> {
        // SAFETY: This is a Python object and hase a base as first element
        unsafe {
            Gc::new_with_custom_finaliser(Self {
                base: Self::obj_type().as_base(),
                inner: RefCell::new(LayoutObjInner::new(root)?),
            })
        }
    }

    fn inner_mut(&self) -> RefMut<LayoutObjInner> {
        self.inner.borrow_mut()
    }

    fn obj_type() -> &'static Type {
        static TYPE: Type = obj_type! {
            name: Qstr::MP_QSTR_LayoutObj,
            locals: &obj_dict!(obj_map! {
                Qstr::MP_QSTR_attach_timer_fn => obj_fn_3!(ui_layout_attach_timer_fn).as_obj(),
                Qstr::MP_QSTR_touch_event => obj_fn_var!(4, 4, ui_layout_touch_event).as_obj(),
                Qstr::MP_QSTR_button_event => obj_fn_var!(3, 3, ui_layout_button_event).as_obj(),
                Qstr::MP_QSTR_progress_event => obj_fn_var!(3, 3, ui_layout_progress_event).as_obj(),
                Qstr::MP_QSTR_usb_event => obj_fn_var!(2, 2, ui_layout_usb_event).as_obj(),
                Qstr::MP_QSTR_timer => obj_fn_2!(ui_layout_timer).as_obj(),
                Qstr::MP_QSTR_paint => obj_fn_1!(ui_layout_paint).as_obj(),
                Qstr::MP_QSTR_request_complete_repaint => obj_fn_1!(ui_layout_request_complete_repaint).as_obj(),
                Qstr::MP_QSTR_trace => obj_fn_2!(ui_layout_trace).as_obj(),
                Qstr::MP_QSTR___del__ => obj_fn_1!(ui_layout_delete).as_obj(),
                Qstr::MP_QSTR_page_count => obj_fn_1!(ui_layout_page_count).as_obj(),
                Qstr::MP_QSTR_button_request => obj_fn_1!(ui_layout_button_request).as_obj(),
                Qstr::MP_QSTR_get_transition_out => obj_fn_1!(ui_layout_get_transition_out).as_obj(),
            }),
        };
        &TYPE
    }

    pub fn skip_first_paint(&self) {
        self.inner_mut().repaint = Repaint::None;
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

extern "C" fn ui_layout_attach_timer_fn(this: Obj, timer_fn: Obj, attach_type: Obj) -> Obj {
    let block = || {
        let this: Gc<LayoutObj> = this.try_into()?;
        this.inner_mut().obj_set_timer_fn(timer_fn);

        let msg = this
            .inner_mut()
            .obj_event(Event::Attach(AttachType::try_from_obj(attach_type)?))?;
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
        let msg = this.inner_mut().obj_event(Event::Touch(event))?;
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
        let msg = this.inner_mut().obj_event(Event::Button(event))?;
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
        let msg = this
            .inner_mut()
            .obj_event(Event::Progress(value, description.into()))?;
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
        let msg = this.inner_mut().obj_event(Event::USB(event))?;
        Ok(msg)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, &Map::EMPTY, block) }
}

extern "C" fn ui_layout_timer(this: Obj, token: Obj) -> Obj {
    let block = || {
        let this: Gc<LayoutObj> = this.try_into()?;
        let event = Event::Timer(token.try_into()?);
        let msg = this.inner_mut().obj_event(event)?;
        Ok(msg)
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn ui_layout_paint(this: Obj) -> Obj {
    let block = || {
        let this: Gc<LayoutObj> = this.try_into()?;
        let painted = this.inner_mut().obj_paint_if_requested().into();
        Ok(painted)
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn ui_layout_request_complete_repaint(this: Obj) -> Obj {
    let block = || {
        let this: Gc<LayoutObj> = this.try_into()?;
        this.inner_mut().obj_request_repaint();
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn ui_layout_page_count(this: Obj) -> Obj {
    let block = || {
        let this: Gc<LayoutObj> = this.try_into()?;
        let page_count = this.inner_mut().obj_page_count();
        Ok(page_count)
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn ui_layout_button_request(this: Obj) -> Obj {
    let block = || {
        let this: Gc<LayoutObj> = this.try_into()?;
        let button_request = this.inner_mut().obj_button_request();
        button_request
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn ui_layout_get_transition_out(this: Obj) -> Obj {
    let block = || {
        let this: Gc<LayoutObj> = this.try_into()?;
        let transition_out = this.inner_mut().obj_get_transition_out();
        Ok(transition_out)
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
        this.inner_mut().obj_trace(callback);
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

#[cfg(not(feature = "ui_debug"))]
extern "C" fn ui_layout_trace(_this: Obj, _callback: Obj) -> Obj {
    Obj::const_none()
}

extern "C" fn ui_layout_delete(this: Obj) -> Obj {
    let block = || {
        let this: Gc<LayoutObj> = this.try_into()?;
        this.inner_mut().obj_delete();
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}
