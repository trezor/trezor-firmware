use crate::{
    error,
    micropython::qstr::Qstr,
    strutil::TString,
    translations::TR,
    ui::{
        button_request::ButtonRequest,
        component::{
            text::paragraphs::{Paragraph, Paragraphs},
            ButtonRequestExt, ComponentExt, SwipeDirection,
        },
        flow::{base::Decision, flow_store, FlowMsg, FlowState, FlowStore, SwipeFlow},
    },
};

use super::super::{
    component::{
        CancelInfoConfirmMsg, Frame, FrameMsg, NumberInputDialog, NumberInputDialogMsg,
        VerticalMenu, VerticalMenuChoiceMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum RequestNumber {
    Number,
    Menu,
    Info,
}

impl FlowState for RequestNumber {
    fn handle_swipe(&self, direction: SwipeDirection) -> Decision<Self> {
        let attach = AttachType::Swipe(direction);
        match (self, direction) {
            (RequestNumber::Number, SwipeDirection::Left) => {
                Decision::Goto(RequestNumber::Menu, attach)
            }
            (RequestNumber::Menu, SwipeDirection::Right) => {
                Decision::Goto(RequestNumber::Number, attach)
            }
            (RequestNumber::Info, SwipeDirection::Right) => {
                Decision::Goto(RequestNumber::Menu, attach)
            }
            _ => Decision::Nothing,
        }
    }

    fn handle_event(&self, msg: FlowMsg) -> Decision<Self> {
        match (self, msg) {
            (RequestNumber::Number, FlowMsg::Info) => {
                Decision::Goto(RequestNumber::Menu, AttachType::Initial)
            }
            (RequestNumber::Menu, FlowMsg::Choice(0)) => {
                Decision::Goto(RequestNumber::Info, AttachType::Swipe(SwipeDirection::Left))
            }
            (RequestNumber::Menu, FlowMsg::Cancelled) => Decision::Goto(
                RequestNumber::Number,
                AttachType::Swipe(SwipeDirection::Right),
            ),
            (RequestNumber::Info, FlowMsg::Cancelled) => {
                Decision::Goto(RequestNumber::Menu, AttachType::Initial)
            }
            (RequestNumber::Number, FlowMsg::Choice(n)) => Decision::Return(FlowMsg::Choice(n)),
            _ => Decision::Nothing,
        }
    }
}

use crate::{
    micropython::{map::Map, obj::Obj, util},
    ui::{
        component::{base::AttachType, swipe_detect::SwipeSettings},
        layout::obj::LayoutObj,
        model_mercury::component::SwipeContent,
    },
};

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_request_number(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, RequestNumber::new_obj) }
}

impl RequestNumber {
    fn new_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let count: u32 = kwargs.get(Qstr::MP_QSTR_count)?.try_into()?;
        let min_count: u32 = kwargs.get(Qstr::MP_QSTR_min_count)?.try_into()?;
        let max_count: u32 = kwargs.get(Qstr::MP_QSTR_max_count)?.try_into()?;
        let description: Obj = kwargs.get(Qstr::MP_QSTR_description)?;
        let info: Obj = kwargs.get(Qstr::MP_QSTR_info)?;
        assert!(description != Obj::const_none());
        assert!(info != Obj::const_none());
        let br_type: TString = kwargs.get(Qstr::MP_QSTR_br_type)?.try_into()?;
        let br_code: u16 = kwargs.get(Qstr::MP_QSTR_br_code)?.try_into()?;

        let description_cb = move |i: u32| {
            TString::try_from(
                description
                    .call_with_n_args(&[i.try_into().unwrap()])
                    .unwrap(),
            )
            .unwrap()
        };
        let info_cb = move |i: u32| {
            TString::try_from(info.call_with_n_args(&[i.try_into().unwrap()]).unwrap()).unwrap()
        };

        let number_input_dialog =
            NumberInputDialog::new(min_count, max_count, count, description_cb)?;
        let content_number_input =
            Frame::left_aligned(title, SwipeContent::new(number_input_dialog))
                .with_menu_button()
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_swipe(SwipeDirection::Up, SwipeSettings::default())
                .with_swipe(SwipeDirection::Left, SwipeSettings::default())
                .map(|msg| match msg {
                    FrameMsg::Button(_) => Some(FlowMsg::Info),
                    FrameMsg::Content(NumberInputDialogMsg(n)) => Some(FlowMsg::Choice(n as usize)),
                })
                .one_button_request(ButtonRequest::from_num(br_code, br_type));

        let content_menu = Frame::left_aligned(
            "".into(),
            VerticalMenu::empty().item(theme::ICON_CHEVRON_RIGHT, TR::buttons__more_info.into()),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(CancelInfoConfirmMsg::Cancelled) => Some(FlowMsg::Cancelled),
            FrameMsg::Button(_) => None,
        });

        let paragraphs_info = Paragraphs::new(Paragraph::new(
            &theme::TEXT_MAIN_GREY_LIGHT,
            info_cb(0), // TODO: get the value
        ));
        let content_info = Frame::left_aligned(
            TR::backup__title_skip.into(),
            SwipeContent::new(paragraphs_info),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Button(CancelInfoConfirmMsg::Cancelled) => Some(FlowMsg::Cancelled),
            _ => None,
        });

        let store = flow_store()
            .add(content_number_input)?
            .add(content_menu)?
            .add(content_info)?;
        let res = SwipeFlow::new(RequestNumber::Number, store)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
