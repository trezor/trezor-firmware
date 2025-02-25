use heapless::Vec;

use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        button_request::ButtonRequest,
        component::{swipe_detect::SwipeSettings, ButtonRequestExt, ComponentExt, MsgMap},
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
    util::{ConfirmValue, ShowInfoParams},
};

const MENU_ITEM_CANCEL: usize = 0;
const MENU_ITEM_FEE_INFO: usize = 1;
const MENU_ITEM_ADDRESS_INFO: usize = 2;
const MENU_ITEM_ACCOUNT_INFO: usize = 3;
const MENU_ITEM_EXTRA_INFO: usize = 4;

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
            (Self::Address, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Address, Direction::Up) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, Direction::Right) => Self::Address.swipe(direction),
            (Self::Menu, Direction::Left) => Self::AccountInfo.swipe(direction),
            (Self::AccountInfo | Self::CancelTap, Direction::Right) => Self::Menu.swipe(direction),
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

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmOutputWithAmount {
    Address,
    Amount,
    Menu,
    AccountInfo,
    CancelTap,
}

impl FlowController for ConfirmOutputWithAmount {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Address | Self::Amount, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Address, Direction::Up) => Self::Amount.swipe(direction),
            (Self::Amount, Direction::Up) => self.return_msg(FlowMsg::Confirmed),
            (Self::Amount, Direction::Down) => Self::Address.swipe(direction),
            (Self::Menu, Direction::Right) => Self::Address.swipe(direction),
            (Self::AccountInfo | Self::CancelTap, Direction::Right) => Self::Menu.swipe(direction),
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

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmOutputWithSummary {
    Main,
    MainMenu,
    MainMenuCancel,
    AddressInfo,
    Summary,
    SummaryMenu,
    SummaryMenuCancel,
    FeeInfo,
    Hold,
    HoldMenu,
    HoldMenuCancel,
    AccountInfo,
    ExtraInfo,
}

impl FlowController for ConfirmOutputWithSummary {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Main, Direction::Left) => Self::MainMenu.swipe(direction),
            (Self::Main, Direction::Up) => Self::Summary.swipe(direction),
            (Self::MainMenu, Direction::Right) => Self::Main.swipe(direction),
            (Self::MainMenuCancel, Direction::Right) => Self::MainMenu.swipe(direction),
            (Self::AddressInfo, Direction::Right) => Self::MainMenu.swipe(direction),
            (Self::AccountInfo, Direction::Right) => Self::MainMenu.swipe(direction),
            (Self::Summary, Direction::Left) => Self::SummaryMenu.swipe(direction),
            (Self::Summary, Direction::Up) => Self::Hold.swipe(direction),
            (Self::Summary, Direction::Down) => Self::Main.swipe(direction),
            (Self::SummaryMenu, Direction::Right) => Self::Summary.swipe(direction),
            (Self::SummaryMenuCancel, Direction::Right) => Self::SummaryMenu.swipe(direction),
            (Self::ExtraInfo, Direction::Right) => Self::SummaryMenu.swipe(direction),
            (Self::FeeInfo, Direction::Right) => Self::SummaryMenu.swipe(direction),
            (Self::Hold, Direction::Left) => Self::HoldMenu.swipe(direction),
            (Self::Hold, Direction::Down) => Self::Summary.swipe(direction),
            (Self::HoldMenu, Direction::Right) => Self::Hold.swipe(direction),
            (Self::HoldMenuCancel, Direction::Right) => Self::HoldMenu.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Main, FlowMsg::Info) => Self::MainMenu.goto(),
            (Self::MainMenu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => {
                Self::MainMenuCancel.swipe_left()
            }
            (Self::AccountInfo, FlowMsg::Cancelled) => Self::MainMenu.goto(),
            (Self::MainMenuCancel, FlowMsg::Cancelled) => Self::MainMenu.goto(),
            (Self::AddressInfo, FlowMsg::Cancelled) => Self::MainMenu.goto(),
            (Self::ExtraInfo, FlowMsg::Cancelled) => Self::SummaryMenu.goto(),
            (Self::Summary, FlowMsg::Info) => Self::SummaryMenu.goto(),
            (Self::SummaryMenu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => {
                Self::SummaryMenuCancel.swipe_left()
            }
            (Self::SummaryMenuCancel, FlowMsg::Cancelled) => Self::SummaryMenu.goto(),
            (Self::Hold, FlowMsg::Info) => Self::HoldMenu.goto(),
            (Self::HoldMenu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => {
                Self::HoldMenuCancel.swipe_left()
            }
            (Self::HoldMenuCancel, FlowMsg::Cancelled) => Self::HoldMenu.goto(),
            (Self::SummaryMenu, FlowMsg::Choice(MENU_ITEM_FEE_INFO)) => Self::FeeInfo.swipe_left(),
            (Self::SummaryMenu, FlowMsg::Choice(MENU_ITEM_EXTRA_INFO)) => {
                Self::ExtraInfo.swipe_left()
            }
            (Self::MainMenu, FlowMsg::Choice(MENU_ITEM_ADDRESS_INFO)) => {
                Self::AddressInfo.swipe_left()
            }
            (Self::MainMenu, FlowMsg::Choice(MENU_ITEM_ACCOUNT_INFO)) => {
                Self::AccountInfo.swipe_left()
            }
            (Self::MainMenu, FlowMsg::Cancelled) => Self::Main.swipe_right(),
            (Self::SummaryMenu, FlowMsg::Cancelled) => Self::Summary.swipe_right(),
            (Self::FeeInfo, FlowMsg::Cancelled) => Self::SummaryMenu.goto(),
            (Self::HoldMenu, FlowMsg::Cancelled) => Self::Hold.swipe_right(),
            (
                Self::MainMenuCancel | Self::SummaryMenuCancel | Self::HoldMenuCancel,
                FlowMsg::Confirmed,
            ) => self.return_msg(FlowMsg::Cancelled),
            (Self::Main, FlowMsg::Cancelled) => Self::MainMenu.goto(),
            (Self::Summary, FlowMsg::Cancelled) => Self::SummaryMenu.goto(),
            (Self::Hold, FlowMsg::Cancelled) => Self::HoldMenu.goto(),
            (Self::Hold, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
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
    .with_swipe(Direction::Right, SwipeSettings::default())
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
    confirm_amount: Option<ConfirmValue>,
    confirm_address: Option<ConfirmValue>,
    confirm_extra: Option<ConfirmValue>,
    summary_items_params: Option<ShowInfoParams>,
    fee_items_params: ShowInfoParams,
    summary_br_name: Option<TString<'static>>,
    summary_br_code: Option<u16>,
    cancel_text: Option<TString<'static>>,
) -> Result<SwipeFlow, error::Error> {
    // Main
    let main_content = confirm_main
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
    main_menu = main_menu.danger(
        theme::ICON_CANCEL,
        cancel_text.unwrap_or(TR::send__cancel_sign.into()),
    );
    unwrap!(main_menu_items.push(MENU_ITEM_CANCEL));
    let content_main_menu = Frame::left_aligned(TString::empty(), main_menu)
        .with_cancel_button()
        .with_swipe(Direction::Right, SwipeSettings::immediate())
        .map(move |msg| match msg {
            VerticalMenuChoiceMsg::Selected(i) => {
                let selected_item = main_menu_items[i];
                Some(FlowMsg::Choice(selected_item))
            }
        });

    // AccountInfo
    let ac = AddressDetails::new(account_title, account, account_path)?;
    let account_content = ac.map(|_| Some(FlowMsg::Cancelled));

    let res = if let Some(confirm_amount) = confirm_amount {
        let confirm_amount = confirm_amount
            .into_layout()?
            .one_button_request(ButtonRequest::from_num(br_code, br_name));

        let mut flow = SwipeFlow::new(&ConfirmOutputWithAmount::Address)?;
        flow.add_page(&ConfirmOutputWithAmount::Address, main_content)?
            .add_page(&ConfirmOutputWithAmount::Amount, confirm_amount)?
            .add_page(&ConfirmOutputWithAmount::Menu, content_main_menu)?
            .add_page(&ConfirmOutputWithAmount::AccountInfo, account_content)?
            .add_page(&ConfirmOutputWithAmount::CancelTap, get_cancel_page())?;
        flow
    } else if let Some(summary_items_params) = summary_items_params {
        // Summary
        let content_summary = summary_items_params
            .into_layout()?
            .one_button_request(ButtonRequest::from_num(
                summary_br_code.unwrap(),
                summary_br_name.unwrap(),
            ))
            .with_pages(|summary_pages| summary_pages + 1);

        // Hold
        let content_hold = Frame::left_aligned(
            TR::send__sign_transaction.into(),
            SwipeContent::new(PromptScreen::new_hold_to_confirm()),
        )
        .with_menu_button()
        .with_footer(TR::instructions__hold_to_sign.into(), None)
        .with_swipe(Direction::Down, SwipeSettings::default())
        .with_swipe(Direction::Left, SwipeSettings::default())
        .map(super::util::map_to_confirm);

        // FeeInfo
        let has_fee_info = !fee_items_params.is_empty();
        let content_fee = fee_items_params.into_layout()?;

        // SummaryMenu
        let mut summary_menu = VerticalMenu::empty();
        let mut summary_menu_items = Vec::<usize, 3>::new();
        if let Some(ref confirm_extra) = confirm_extra {
            summary_menu = summary_menu.item(theme::ICON_CHEVRON_RIGHT, confirm_extra.title());
            unwrap!(summary_menu_items.push(MENU_ITEM_EXTRA_INFO));
        }
        if has_fee_info {
            summary_menu = summary_menu.item(
                theme::ICON_CHEVRON_RIGHT,
                TR::confirm_total__title_fee.into(),
            );
            unwrap!(summary_menu_items.push(MENU_ITEM_FEE_INFO));
        }
        summary_menu = summary_menu.danger(
            theme::ICON_CANCEL,
            cancel_text.unwrap_or(TR::send__cancel_sign.into()),
        );
        unwrap!(summary_menu_items.push(MENU_ITEM_CANCEL));
        let content_summary_menu = Frame::left_aligned(TString::empty(), summary_menu)
            .with_cancel_button()
            .with_swipe(Direction::Right, SwipeSettings::immediate())
            .map(move |msg| match msg {
                VerticalMenuChoiceMsg::Selected(i) => {
                    let selected_item = summary_menu_items[i];
                    Some(FlowMsg::Choice(selected_item))
                }
            });

        // HoldMenu
        let hold_menu = VerticalMenu::empty().danger(
            theme::ICON_CANCEL,
            cancel_text.unwrap_or(TR::send__cancel_sign.into()),
        );
        let content_hold_menu = Frame::left_aligned(TString::empty(), hold_menu)
            .with_cancel_button()
            .with_swipe(Direction::Right, SwipeSettings::immediate())
            .map(super::util::map_to_choice);

        let mut flow = SwipeFlow::new(&ConfirmOutputWithSummary::Main)?;
        flow.add_page(&ConfirmOutputWithSummary::Main, main_content)?
            .add_page(&ConfirmOutputWithSummary::MainMenu, content_main_menu)?
            .add_page(&ConfirmOutputWithSummary::MainMenuCancel, get_cancel_page())?;
        if let Some(confirm_address) = confirm_address {
            let address_content = confirm_address.into_layout()?;
            flow.add_page(&ConfirmOutputWithSummary::AddressInfo, address_content)?;
        } else {
            // dummy page - this will never be shown since there is no menu item pointing to
            // it, but the page has to exist in the flow
            flow.add_page(
                &ConfirmOutputWithSummary::AddressInfo,
                Frame::left_aligned(TString::empty(), VerticalMenu::empty())
                    .map(|_| Some(FlowMsg::Cancelled)),
            )?;
        }
        flow.add_page(&ConfirmOutputWithSummary::Summary, content_summary)?
            .add_page(&ConfirmOutputWithSummary::SummaryMenu, content_summary_menu)?
            .add_page(
                &ConfirmOutputWithSummary::SummaryMenuCancel,
                get_cancel_page(),
            )?
            .add_page(&ConfirmOutputWithSummary::FeeInfo, content_fee)?
            .add_page(&ConfirmOutputWithSummary::Hold, content_hold)?
            .add_page(&ConfirmOutputWithSummary::HoldMenu, content_hold_menu)?
            .add_page(&ConfirmOutputWithSummary::HoldMenuCancel, get_cancel_page())?
            .add_page(&ConfirmOutputWithSummary::AccountInfo, account_content)?;
        if let Some(confirm_extra) = confirm_extra {
            let extra_content = confirm_extra.into_layout()?;
            flow.add_page(&ConfirmOutputWithSummary::ExtraInfo, extra_content)?;
        }
        flow
    } else {
        let mut flow = SwipeFlow::new(&ConfirmOutput::Address)?;
        flow.add_page(&ConfirmOutput::Address, main_content)?
            .add_page(&ConfirmOutput::Menu, content_main_menu)?
            .add_page(&ConfirmOutput::AccountInfo, account_content)?
            .add_page(&ConfirmOutput::CancelTap, get_cancel_page())?;
        flow
    };

    Ok(res)
}
