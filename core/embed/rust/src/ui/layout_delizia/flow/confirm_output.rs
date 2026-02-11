use heapless::Vec;

use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        button_request::ButtonRequest,
        component::{ButtonRequestExt, ComponentExt, MsgMap},
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::Direction,
    },
};

use super::{
    super::{
        component::{
            AddressDetails, Frame, FrameMsg, PromptMsg, PromptScreen, SwipeContent, VerticalMenu,
            VerticalMenuChoiceMsg,
        },
        theme,
    },
    util::ConfirmValue,
};

const MENU_ITEM_CANCEL: usize = 0;
const MENU_ITEM_ADDRESS_INFO: usize = 1;
const MENU_ITEM_ACCOUNT_INFO: usize = 2;

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmOutput {
    Address,
    Menu,
    AccountInfo,
    CancelTap,
}

impl FlowController for ConfirmOutput {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Address, Direction::Up) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (_, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => Self::CancelTap.swipe_left(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_ACCOUNT_INFO)) => Self::AccountInfo.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Address.swipe_right(),
            (Self::CancelTap, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            (_, FlowMsg::Cancelled) => Self::Menu.goto(),
            _ => self.do_nothing(),
        }
    }
}

fn get_cancel_page(
) -> MsgMap<Frame<SwipeContent<PromptScreen>>, impl Fn(FrameMsg<PromptMsg>) -> Option<FlowMsg>> {
    Frame::left_aligned(
        TR::send__cancel_sign.into(),
        SwipeContent::new(PromptScreen::new_tap_to_cancel()),
    )
    .with_cancel_button()
    .with_footer(TR::instructions__tap_to_confirm.into(), None)
    .map(super::util::map_to_confirm)
}

#[allow(clippy::too_many_arguments)]
pub fn new_confirm_output(
    confirm_main: ConfirmValue,
    account_title: TString<'static>,
    account: Option<TString<'static>>,
    account_path: Option<TString<'static>>,
    br_name: TString<'static>,
    br_code: u16,
    confirm_address: Option<ConfirmValue>,
    cancel_text: Option<TString<'static>>,
) -> Result<SwipeFlow, error::Error> {
    // Main
    let main_content = confirm_main
        .with_flow_menu(true)
        .into_layout()?
        .one_button_request(ButtonRequest::from_num(br_code, br_name));

    // MainMenu
    let mut main_menu = VerticalMenu::empty();
    let mut main_menu_items = Vec::<usize, 3>::new();
    if let Some(ref confirm_address) = confirm_address {
        main_menu = main_menu.item(theme::ICON_CHEVRON_RIGHT, confirm_address.title());
        unwrap!(main_menu_items.push(MENU_ITEM_ADDRESS_INFO));
    }
    if account.is_some() && account_path.is_some() {
        main_menu = main_menu.item(
            theme::ICON_CHEVRON_RIGHT,
            TR::address_details__account_info.into(),
        );
        unwrap!(main_menu_items.push(MENU_ITEM_ACCOUNT_INFO));
    }
    main_menu = main_menu.cancel_item(cancel_text.unwrap_or(TR::send__cancel_sign.into()));
    unwrap!(main_menu_items.push(MENU_ITEM_CANCEL));
    let content_main_menu = Frame::left_aligned(TString::empty(), main_menu)
        .with_cancel_button()
        .map(move |msg| match msg {
            VerticalMenuChoiceMsg::Selected(i) => {
                let selected_item = main_menu_items[i];
                Some(FlowMsg::Choice(selected_item))
            }
        });

    // AccountInfo
    let ac = AddressDetails::new(account_title, account, account_path)?;
    let account_content = ac.map(|_| Some(FlowMsg::Cancelled));

    let mut flow = SwipeFlow::new(&ConfirmOutput::Address)?;
    flow.add_page(&ConfirmOutput::Address, main_content)?
        .add_page(&ConfirmOutput::Menu, content_main_menu)?
        .add_page(&ConfirmOutput::AccountInfo, account_content)?
        .add_page(&ConfirmOutput::CancelTap, get_cancel_page())?;

    Ok(flow)
}
