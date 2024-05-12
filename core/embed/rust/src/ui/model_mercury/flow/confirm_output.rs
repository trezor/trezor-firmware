use crate::{
    error,
    micropython::qstr::Qstr,
    strutil::TString,
    translations::TR,
    ui::{
        component::{ComponentExt, SwipeDirection},
        flow::{base::Decision, flow_store, FlowMsg, FlowState, FlowStore, SwipeFlow, SwipePage},
    },
};

use super::super::{
    component::{
        AddressDetails, Frame, FrameMsg, PromptScreen, VerticalMenu, VerticalMenuChoiceMsg,
    },
    theme,
};

use super::util::ConfirmBlobParams;

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum ConfirmOutput {
    Address,
    Amount,
    // Tap,
    Menu,
    AccountInfo,
    CancelTap,
}

impl FlowState for ConfirmOutput {
    fn handle_swipe(&self, direction: SwipeDirection) -> Decision<Self> {
        match (self, direction) {
            (ConfirmOutput::Address | ConfirmOutput::Amount, SwipeDirection::Left) => {
                Decision::Goto(ConfirmOutput::Menu, direction)
            }
            (ConfirmOutput::Address, SwipeDirection::Up) => {
                Decision::Goto(ConfirmOutput::Amount, direction)
            }
            (ConfirmOutput::Amount, SwipeDirection::Up) => Decision::Return(FlowMsg::Confirmed),
            (ConfirmOutput::Amount, SwipeDirection::Down) => {
                Decision::Goto(ConfirmOutput::Address, direction)
            }
            (ConfirmOutput::Menu, SwipeDirection::Right) => {
                Decision::Goto(ConfirmOutput::Address, direction)
            }
            (ConfirmOutput::Menu, SwipeDirection::Left) => {
                Decision::Goto(ConfirmOutput::AccountInfo, direction)
            }
            (ConfirmOutput::AccountInfo | ConfirmOutput::CancelTap, SwipeDirection::Right) => {
                Decision::Goto(ConfirmOutput::Menu, direction)
            }
            _ => Decision::Nothing,
        }
    }

    fn handle_event(&self, msg: FlowMsg) -> Decision<Self> {
        match (self, msg) {
            (_, FlowMsg::Info) => Decision::Goto(ConfirmOutput::Menu, SwipeDirection::Left),
            (ConfirmOutput::Menu, FlowMsg::Choice(0)) => {
                Decision::Goto(ConfirmOutput::AccountInfo, SwipeDirection::Left)
            }
            (ConfirmOutput::Menu, FlowMsg::Choice(1)) => {
                Decision::Goto(ConfirmOutput::CancelTap, SwipeDirection::Left)
            }
            (ConfirmOutput::Menu, FlowMsg::Cancelled) => {
                Decision::Goto(ConfirmOutput::Address, SwipeDirection::Right)
            }
            (ConfirmOutput::CancelTap, FlowMsg::Confirmed) => Decision::Return(FlowMsg::Cancelled),
            (_, FlowMsg::Cancelled) => Decision::Goto(ConfirmOutput::Menu, SwipeDirection::Right),
            _ => Decision::Nothing,
        }
    }
}

use crate::{
    micropython::{map::Map, obj::Obj, util},
    ui::layout::obj::LayoutObj,
};

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_confirm_output(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, ConfirmOutput::new_obj) }
}

impl ConfirmOutput {
    const EXTRA_PADDING: i16 = 6;

    fn new_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
        let title: Option<TString> = kwargs.get(Qstr::MP_QSTR_title)?.try_into_option()?;
        let account: Option<TString> = kwargs.get(Qstr::MP_QSTR_account)?.try_into_option()?;
        let account_path: Option<TString> =
            kwargs.get(Qstr::MP_QSTR_account_path)?.try_into_option()?;

        let address: Obj = kwargs.get(Qstr::MP_QSTR_address)?;
        let amount: Obj = kwargs.get(Qstr::MP_QSTR_amount)?;

        let chunkify: bool = kwargs.get_or(Qstr::MP_QSTR_chunkify, false)?;
        let text_mono: bool = kwargs.get_or(Qstr::MP_QSTR_text_mono, true)?;

        // Address
        let content_address = ConfirmBlobParams::new(TR::words__address.into(), address, None)
            .with_subtitle(title)
            .with_menu_button()
            .with_footer(TR::instructions__swipe_up.into(), None)
            .with_chunkify(chunkify)
            .with_text_mono(text_mono)
            .into_layout()?;
        // .one_button_request(ButtonRequestCode::ConfirmOutput, br_type);

        // Amount
        let content_amount = ConfirmBlobParams::new(TR::words__amount.into(), amount, None)
            .with_subtitle(title)
            .with_menu_button()
            .with_footer(TR::instructions__swipe_up.into(), None)
            .with_text_mono(text_mono)
            .into_layout()?;
        // .one_button_request(ButtonRequestCode::ConfirmOutput, br_type);

        // Menu
        let content_menu = Frame::left_aligned(
            "".into(),
            VerticalMenu::empty()
                .item(theme::ICON_CHEVRON_RIGHT, "Account info".into())
                .danger(theme::ICON_CANCEL, "Cancel sign".into()),
        )
        .with_cancel_button()
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

        // AccountInfo
        let ad = AddressDetails::new(TR::send__send_from.into(), account, account_path)?;
        let content_account = SwipePage::horizontal(ad).map(|_| Some(FlowMsg::Cancelled));

        // CancelTap
        let content_cancel_tap = Frame::left_aligned(
            TR::send__cancel_sign.into(),
            PromptScreen::new_tap_to_cancel(),
        )
        .with_cancel_button()
        .with_footer(TR::instructions__tap_to_confirm.into(), None)
        .map(|msg| match msg {
            FrameMsg::Content(()) => Some(FlowMsg::Confirmed),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

        let store = flow_store()
            .add(content_address)?
            .add(content_amount)?
            .add(content_menu)?
            .add(content_account)?
            .add(content_cancel_tap)?;
        let res = SwipeFlow::new(ConfirmOutput::Address, store)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
