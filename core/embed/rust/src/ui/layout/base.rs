use crate::ui::{
    button_request::ButtonRequest,
    component::{base::AttachType, Event, EventCtx},
};

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum LayoutState {
    Initial,
    Attached(Option<ButtonRequest>),
    Transitioning(AttachType),
    Done,
}

pub trait Layout<T> {
    fn place(&mut self);
    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<LayoutState>;
    fn value(&self) -> Option<&T>;
    fn paint(&mut self);
}

#[cfg(feature = "micropython")]
mod micropython {
    use crate::micropython::{
        macros::{obj_dict, obj_map, obj_type},
        obj::Obj,
        qstr::Qstr,
        simple_type::SimpleTypeObj,
        typ::Type,
    };

    use super::LayoutState;

    static STATE_INITIAL_TYPE: Type = obj_type! {
        name: Qstr::MP_QSTR_INITIAL,
        base: LAYOUT_STATE_TYPE,
    };

    static STATE_ATTACHED_TYPE: Type = obj_type! {
        name: Qstr::MP_QSTR_ATTACHED,
        base: LAYOUT_STATE_TYPE,
    };

    static STATE_TRANSITIONING_TYPE: Type = obj_type! {
        name: Qstr::MP_QSTR_TRANSITIONING,
        base: LAYOUT_STATE_TYPE,
    };

    static STATE_DONE_TYPE: Type = obj_type! {
        name: Qstr::MP_QSTR_DONE,
        base: LAYOUT_STATE_TYPE,
    };

    pub static STATE_INITIAL: SimpleTypeObj = SimpleTypeObj::new(&STATE_INITIAL_TYPE);
    pub static STATE_ATTACHED: SimpleTypeObj = SimpleTypeObj::new(&STATE_ATTACHED_TYPE);
    pub static STATE_TRANSITIONING: SimpleTypeObj = SimpleTypeObj::new(&STATE_TRANSITIONING_TYPE);
    pub static STATE_DONE: SimpleTypeObj = SimpleTypeObj::new(&STATE_DONE_TYPE);

    static LAYOUT_STATE_TYPE: Type = obj_type! {
        name: Qstr::MP_QSTR_LayoutState,
        locals: &obj_dict! { obj_map! {
            Qstr::MP_QSTR_INITIAL => STATE_INITIAL.as_obj(),
            Qstr::MP_QSTR_ATTACHED => STATE_ATTACHED.as_obj(),
            Qstr::MP_QSTR_TRANSITIONING => STATE_TRANSITIONING.as_obj(),
            Qstr::MP_QSTR_DONE => STATE_DONE.as_obj(),
        } },
    };

    pub static LAYOUT_STATE: SimpleTypeObj = SimpleTypeObj::new(&LAYOUT_STATE_TYPE);

    impl From<LayoutState> for Obj {
        fn from(state: LayoutState) -> Self {
            match state {
                LayoutState::Initial => STATE_INITIAL.as_obj(),
                LayoutState::Attached(_) => STATE_ATTACHED.as_obj(),
                LayoutState::Transitioning(_) => STATE_TRANSITIONING.as_obj(),
                LayoutState::Done => STATE_DONE.as_obj(),
            }
        }
    }
}

#[cfg(feature = "micropython")]
pub use micropython::*;
