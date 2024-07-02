use crate::{
    error,
    micropython::{iter::IterBuf, qstr::Qstr},
    strutil::TString,
    translations::TR,
    ui::{
        button_request::ButtonRequest,
        component::{ButtonRequestExt, ComponentExt, SwipeDirection},
        flow::{base::Decision, flow_store, FlowMsg, FlowState, FlowStore, SwipeFlow},
    },
};

use super::super::{
    component::{Frame, FrameMsg, PromptScreen, VerticalMenu, VerticalMenuChoiceMsg},
    theme,
};

use super::util::ShowInfoParams;

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum ConfirmSummary {
    Summary,
    Hold,
    Menu,
    FeeInfo,
    AccountInfo,
    CancelTap,
}

impl FlowState for ConfirmSummary {
    fn handle_swipe(&self, direction: SwipeDirection) -> Decision<Self> {
        let attach = AttachType::Swipe(direction);
        match (self, direction) {
            (ConfirmSummary::Summary | ConfirmSummary::Hold, SwipeDirection::Left) => {
                Decision::Goto(ConfirmSummary::Menu, attach)
            }
            (ConfirmSummary::Summary, SwipeDirection::Up) => {
                Decision::Goto(ConfirmSummary::Hold, attach)
            }
            (ConfirmSummary::Hold, SwipeDirection::Down) => {
                Decision::Goto(ConfirmSummary::Summary, attach)
            }
            (ConfirmSummary::Menu, SwipeDirection::Right) => {
                Decision::Goto(ConfirmSummary::Summary, attach)
            }
            (ConfirmSummary::Menu, SwipeDirection::Left) => {
                Decision::Goto(ConfirmSummary::FeeInfo, attach)
            }
            (
                ConfirmSummary::AccountInfo | ConfirmSummary::FeeInfo | ConfirmSummary::CancelTap,
                SwipeDirection::Right,
            ) => Decision::Goto(ConfirmSummary::Menu, attach),
            _ => Decision::Nothing,
        }
    }

    fn handle_event(&self, msg: FlowMsg) -> Decision<Self> {
        match (self, msg) {
            (_, FlowMsg::Info) => Decision::Goto(ConfirmSummary::Menu, AttachType::Initial),
            (ConfirmSummary::Hold, FlowMsg::Confirmed) => Decision::Return(FlowMsg::Confirmed),
            (ConfirmSummary::Menu, FlowMsg::Choice(0)) => Decision::Goto(
                ConfirmSummary::FeeInfo,
                AttachType::Swipe(SwipeDirection::Left),
            ),
            (ConfirmSummary::Menu, FlowMsg::Choice(1)) => Decision::Goto(
                ConfirmSummary::AccountInfo,
                AttachType::Swipe(SwipeDirection::Left),
            ),
            (ConfirmSummary::Menu, FlowMsg::Choice(2)) => Decision::Goto(
                ConfirmSummary::CancelTap,
                AttachType::Swipe(SwipeDirection::Left),
            ),
            (ConfirmSummary::Menu, FlowMsg::Cancelled) => Decision::Goto(
                ConfirmSummary::Summary,
                AttachType::Swipe(SwipeDirection::Right),
            ),
            (ConfirmSummary::CancelTap, FlowMsg::Confirmed) => Decision::Return(FlowMsg::Cancelled),
            (_, FlowMsg::Cancelled) => Decision::Goto(ConfirmSummary::Menu, AttachType::Initial),
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
pub extern "C" fn new_confirm_summary(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, ConfirmSummary::new_obj) }
}

impl ConfirmSummary {
    fn new_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let items: Obj = kwargs.get(Qstr::MP_QSTR_items)?;
        let account_items: Obj = kwargs.get(Qstr::MP_QSTR_account_items)?;
        let fee_items: Obj = kwargs.get(Qstr::MP_QSTR_fee_items)?;
        let br_type: TString = kwargs.get(Qstr::MP_QSTR_br_type)?.try_into()?;
        let br_code: u16 = kwargs.get(Qstr::MP_QSTR_br_code)?.try_into()?;

        // Summary
        let mut summary = ShowInfoParams::new(title)
            .with_menu_button()
            .with_footer(TR::instructions__swipe_up.into(), None)
            .with_swipe_up();
        for pair in IterBuf::new().try_iterate(items)? {
            let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
            summary = unwrap!(summary.add(label, value));
        }
        let content_summary = summary
            .into_layout()?
            .one_button_request(ButtonRequest::from_num(br_code, br_type))
            // Summary(1) + Hold(1)
            .with_pages(|summary_pages| summary_pages + 1);

        // Hold to confirm
        let content_hold = Frame::left_aligned(
            TR::send__sign_transaction.into(),
            SwipeContent::new(PromptScreen::new_hold_to_confirm()),
        )
        .with_menu_button()
        .with_footer(TR::instructions__hold_to_sign.into(), None)
        .with_swipe(SwipeDirection::Down, SwipeSettings::default())
        .with_swipe(SwipeDirection::Left, SwipeSettings::default())
        .map(|msg| match msg {
            FrameMsg::Content(()) => Some(FlowMsg::Confirmed),
            FrameMsg::Button(_) => Some(FlowMsg::Info),
        });

        // Menu
        let content_menu = Frame::left_aligned(
            "".into(),
            VerticalMenu::empty()
                .item(theme::ICON_CHEVRON_RIGHT, "Fee info".into())
                .item(theme::ICON_CHEVRON_RIGHT, "Account info".into())
                .danger(theme::ICON_CANCEL, "Cancel sign".into()),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

        // FeeInfo
        let mut fee = ShowInfoParams::new(TR::confirm_total__title_fee.into()).with_cancel_button();
        for pair in IterBuf::new().try_iterate(fee_items)? {
            let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
            fee = unwrap!(fee.add(label, value));
        }
        let content_fee = fee.into_layout()?;

        // AccountInfo
        let mut account = ShowInfoParams::new(TR::send__send_from.into()).with_cancel_button();
        for pair in IterBuf::new().try_iterate(account_items)? {
            let [label, value]: [TString; 2] = util::iter_into_array(pair)?;
            account = unwrap!(account.add(label, value));
        }
        let content_account = account.into_layout()?;

        // CancelTap
        let content_cancel_tap = Frame::left_aligned(
            TR::send__cancel_sign.into(),
            PromptScreen::new_tap_to_cancel(),
        )
        .with_cancel_button()
        .with_footer(TR::instructions__tap_to_confirm.into(), None)
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(()) => Some(FlowMsg::Confirmed),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

        let store = flow_store()
            .add(content_summary)?
            .add(content_hold)?
            .add(content_menu)?
            .add(content_fee)?
            .add(content_account)?
            .add(content_cancel_tap)?;
        let res = SwipeFlow::new(ConfirmSummary::Summary, store)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
