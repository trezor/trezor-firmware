use core::{
    cell::{RefCell, RefMut},
    convert::{TryFrom, TryInto},
    marker::PhantomData,
    ops::{Deref, DerefMut},
};
#[cfg(feature = "touch")]
use num_traits::{FromPrimitive, ToPrimitive};

#[cfg(feature = "button")]
use crate::ui::event::ButtonEvent;

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
        component::{
            base::{AttachType, TimerToken},
            Component, Event, EventCtx, Never,
        },
        display,
        event::USBEvent,
        CommonUI, ModelUI,
    },
};

use super::base::{Layout, LayoutState};

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

pub trait ComponentMaybeTrace: Component + ComponentMsgObj + MaybeTrace {}
impl<T> ComponentMaybeTrace for T where T: Component + ComponentMsgObj + MaybeTrace {}

pub struct RootComponent<T, M>
where
    T: Component,
    M: CommonUI,
{
    inner: T,
    returned_value: Option<Result<Obj, Error>>,
    _features: PhantomData<M>,
}

impl<T, M> RootComponent<T, M>
where
    T: ComponentMaybeTrace,
    M: CommonUI,
{
    pub fn new(component: T) -> Self {
        Self {
            inner: component,
            returned_value: None,
            _features: PhantomData,
        }
    }
}

impl<T> Layout<Result<Obj, Error>> for RootComponent<T, ModelUI>
where
    T: Component + ComponentMsgObj,
{
    fn place(&mut self) {
        self.inner.place(ModelUI::SCREEN);
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<LayoutState> {
        if let Some(msg) = self.inner.event(ctx, event) {
            self.returned_value = Some(self.inner.msg_try_into_obj(msg));
            Some(LayoutState::Done)
        } else if matches!(event, Event::Attach(_)) {
            Some(LayoutState::Attached(ctx.button_request().take()))
        } else {
            None
        }
    }

    fn value(&self) -> Option<&Result<Obj, Error>> {
        self.returned_value.as_ref()
    }

    fn paint(&mut self) {
        render_on_display(None, Some(Color::black()), |target| {
            self.inner.render(target);
        });
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for RootComponent<T, ModelUI>
where
    T: Component + crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.inner.trace(t);
    }
}

pub trait LayoutMaybeTrace: Layout<Result<Obj, Error>> + MaybeTrace {}
impl<T> LayoutMaybeTrace for T where T: Layout<Result<Obj, Error>> + MaybeTrace {}

#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
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
    root: Option<GcBox<dyn LayoutMaybeTrace>>,
    event_ctx: EventCtx,
    timer_fn: Obj,
    page_count: u16,
    repaint: Repaint,
    transition_out: AttachType,
    button_request: Option<ButtonRequest>,
}

impl LayoutObjInner {
    /// Create a new `LayoutObj`, wrapping a root component.
    #[inline(never)]
    pub fn new(root: impl LayoutMaybeTrace + 'static) -> Result<Self, Error> {
        let root = GcBox::new(root)?;

        let mut new = Self {
            root: Some(gc::coerce!(LayoutMaybeTrace, root)),
            event_ctx: EventCtx::new(),
            timer_fn: Obj::const_none(),
            page_count: 1,
            repaint: Repaint::Full,
            transition_out: AttachType::Initial,
            button_request: None,
        };

        // invoke the initial placement
        new.root_mut().place();
        // cause a repaint pass to update the number of pages
        let msg = new.obj_event(Event::RequestPaint);
        assert!(matches!(msg, Ok(s) if s == Obj::const_none()));

        Ok(new)
    }

    fn obj_delete(&mut self) {
        self.root = None;
    }

    /// Timer callback is expected to be a callable object of the following
    /// form: `def timer(token: int, duration_ms: int)`.
    fn obj_set_timer_fn(&mut self, timer_fn: Obj) {
        self.timer_fn = timer_fn;
    }

    fn root(&self) -> &impl Deref<Target = dyn LayoutMaybeTrace> {
        unwrap!(self.root.as_ref())
    }

    fn root_mut(&mut self) -> &mut impl DerefMut<Target = dyn LayoutMaybeTrace> {
        unwrap!(self.root.as_mut())
    }

    fn obj_request_repaint(&mut self) {
        self.repaint = Repaint::Full;
        let mut event_ctx = EventCtx::new();
        let paint_msg = self.root_mut().event(&mut event_ctx, Event::RequestPaint);
        // paint_msg must not change the state
        assert!(paint_msg.is_none());
        // there must be no timers set
        assert!(event_ctx.pop_timer().is_none());
    }

    /// Run an event pass over the component tree. After the traversal, any
    /// pending timers are drained into `self.timer_callback`. Returns `Err`
    /// in case the timer callback raises or one of the components returns
    /// an error, `Ok` with the message otherwise.
    fn obj_event(&mut self, event: Event) -> Result<Obj, Error> {
        let root = unwrap!(self.root.as_mut());

        // Get the event context ready for a new event
        self.event_ctx.clear();

        // Send the event down the component tree.
        let msg = root.event(&mut self.event_ctx, event);

        match msg {
            Some(LayoutState::Done) => return Ok(msg.into()), // short-circuit
            Some(LayoutState::Attached(br)) => {
                assert!(self.button_request.is_none());
                self.button_request = br;
            }
            Some(LayoutState::Transitioning(t)) => self.transition_out = t,
            _ => (),
        };

        // Place the root component on the screen in case it was requested.
        if self.event_ctx.needs_place() {
            root.place();
        }

        // Check if we should repaint next time
        if self.event_ctx.needs_repaint_root() {
            self.obj_request_repaint();
        } else if self.event_ctx.needs_repaint() && self.repaint == Repaint::None {
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

        // Update page count if it changed
        if let Some(count) = self.event_ctx.page_count() {
            self.page_count = count as u16;
        }

        Ok(msg.into())
    }

    /// Run a paint pass over the component tree. Returns true if any component
    /// actually requested painting since last invocation of the function.
    fn obj_paint_if_requested(&mut self) -> bool {
        display::sync();

        if self.repaint != Repaint::None {
            self.repaint = Repaint::None;
            self.root_mut().paint();
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

        // (The Reasons being, root is a `Gc<dyn LayoutMaybeTrace>`, and `Gc` does not
        // implement `Trace`, and `dyn LayoutMaybeTrace` is unsized so we can't deref it
        // to claim that it implements `Trace`, and we also can't upcast it to
        // `&dyn Trace` because trait upcasting is unstable.
        // Luckily, calling `root.trace()` works perfectly fine in spite of the above.)
        tracer.root(&|t| {
            self.root().trace(t);
        });
    }

    fn obj_page_count(&self) -> Obj {
        self.page_count.into()
    }

    fn obj_button_request(&mut self) -> Result<Obj, Error> {
        match self.button_request.take() {
            None => Ok(Obj::const_none()),
            Some(ButtonRequest { code, name }) => (code.num().into(), name.try_into()?).try_into(),
        }
    }

    fn obj_get_transition_out(&self) -> Obj {
        self.transition_out.to_obj()
    }

    fn obj_return_value(&self) -> Result<Obj, Error> {
        self.root()
            .value()
            .cloned()
            .unwrap_or(Ok(Obj::const_none()))
    }
}

impl LayoutObj {
    /// Create a new `LayoutObj`, wrapping a root component.
    pub fn new<T: ComponentMaybeTrace + 'static>(root: T) -> Result<Gc<Self>, Error> {
        let root_component = RootComponent::new(root);
        Self::new_root(root_component)
    }

    pub fn new_root(root: impl LayoutMaybeTrace + 'static) -> Result<Gc<Self>, Error> {
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
                Qstr::MP_QSTR_return_value => obj_fn_1!(ui_layout_return_value).as_obj(),
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
            .obj_event(Event::Attach(AttachType::try_from_obj(attach_type)?));
        msg
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

extern "C" fn ui_layout_return_value(this: Obj) -> Obj {
    let block = || {
        let this: Gc<LayoutObj> = this.try_into()?;
        let value = this.inner_mut().obj_return_value();
        value
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
