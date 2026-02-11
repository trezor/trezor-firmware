use heapless::Vec;

use crate::{
    error,
    strutil::TString,
    time::Duration,
    translations::TR,
    ui::{
        button_request::ButtonRequest,
        component::{
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs},
            ButtonRequestExt, ComponentExt, MsgMap,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::{Direction, LinearPlacement},
    },
};

use super::super::{
    component::Button,
    firmware::{
        ActionBar, Header, Hint, ShortMenuVec, TextScreen, TextScreenMsg, VerticalMenu,
        VerticalMenuScreen, VerticalMenuScreenMsg,
    },
    flow::util::content_menu_info,
    theme::{self, gradient::Gradient},
};

const MENU_ITEM_CANCEL: usize = 0;
const MENU_ITEM_ADDRESS_INFO: usize = 1;
const MENU_ITEM_ACCOUNT_INFO: usize = 2;

const TIMEOUT: Duration = Duration::from_secs(2);

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmOutput {
    Address,
    Menu,
    AccountInfo,
    Cancel,
    Cancelled,
}

impl FlowController for ConfirmOutput {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Address, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Address, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_CANCEL)) => Self::Cancel.goto(),
            (Self::Menu, FlowMsg::Choice(MENU_ITEM_ACCOUNT_INFO)) => Self::AccountInfo.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Address.goto(),
            (Self::AccountInfo, FlowMsg::Cancelled) => Self::Menu.goto(),
            (Self::Cancel, FlowMsg::Confirmed) => Self::Cancelled.goto(),
            (Self::Cancel, FlowMsg::Cancelled) => Self::Menu.goto(),
            (Self::Cancelled, _) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

fn content_cancel(
) -> MsgMap<TextScreen<Paragraphs<Paragraph<'static>>>, impl Fn(TextScreenMsg) -> Option<FlowMsg>> {
    TextScreen::new(
        Paragraph::new(&theme::TEXT_REGULAR, TR::send__cancel_sign)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical()),
    )
    .with_header(Header::new(TR::words__send.into()))
    .with_action_bar(ActionBar::new_double(
        Button::with_icon(theme::ICON_CHEVRON_LEFT),
        Button::with_text(TR::buttons__cancel.into())
            .styled(theme::button_actionbar_danger())
            .with_gradient(Gradient::Alert),
    ))
    .map(|msg| match msg {
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
        _ => None,
    })
}

fn content_main_menu(
    address_title: TString<'static>,
    address_params: bool,
    account_params: bool,
    cancel_menu_label: TString<'static>,
) -> MsgMap<VerticalMenuScreen<ShortMenuVec>, impl Fn(VerticalMenuScreenMsg) -> Option<FlowMsg>> {
    let mut main_menu = VerticalMenu::<ShortMenuVec>::empty();
    let mut main_menu_items = Vec::<usize, 3>::new();
    if address_params {
        main_menu.item(Button::new_menu_item(
            address_title,
            theme::menu_item_title(),
        ));
        unwrap!(main_menu_items.push(MENU_ITEM_ADDRESS_INFO));
    }
    if account_params {
        main_menu.item(Button::new_menu_item(
            TR::address_details__account_info.into(),
            theme::menu_item_title(),
        ));
        unwrap!(main_menu_items.push(MENU_ITEM_ACCOUNT_INFO));
    }
    main_menu.item(Button::new_cancel_menu_item(cancel_menu_label));
    unwrap!(main_menu_items.push(MENU_ITEM_CANCEL));

    VerticalMenuScreen::<ShortMenuVec>::new(main_menu)
        .with_header(Header::new(TString::empty()).with_close_button())
        .map(move |msg| match msg {
            VerticalMenuScreenMsg::Selected(i) => {
                let selected_item = main_menu_items[i];
                Some(FlowMsg::Choice(selected_item))
            }
            VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
            _ => None,
        })
}

#[allow(clippy::too_many_arguments)]
pub fn new_confirm_output(
    title: Option<TString<'static>>,
    subtitle: Option<TString<'static>>,
    main_paragraphs: ParagraphVecShort<'static>,
    br_name: TString<'static>,
    br_code: u16,
    account_title: TString<'static>,
    account_paragraphs: Option<ParagraphVecShort<'static>>,
    address_title: Option<TString<'static>>,
    address_paragraph: Option<Paragraph<'static>>,
    cancel_menu_label: Option<TString<'static>>,
) -> Result<SwipeFlow, error::Error> {
    let cancel_menu_label = cancel_menu_label.unwrap_or(TR::buttons__cancel.into());
    let address_menu_item = address_paragraph.is_some();
    let account_menu_item = account_paragraphs.is_some();
    let address_title = address_title.unwrap_or(TR::words__address.into());
    let account_subtitle = Some(TR::send__send_from.into());

    // Main
    let content_main =
        TextScreen::new(main_paragraphs.into_paragraphs().with_placement(
            LinearPlacement::vertical().with_spacing(theme::TEXT_VERTICAL_SPACING),
        ))
        .with_flow_menu(true)
        .with_header(Header::new(title.unwrap_or(TString::empty())).with_menu_button())
        .with_subtitle(subtitle.unwrap_or(TString::empty()))
        .with_hint(Hint::new_page_counter())
        .with_action_bar(ActionBar::new_single(Button::with_text(
            TR::buttons__continue.into(),
        )))
        .map(|msg| match msg {
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
            TextScreenMsg::Menu => Some(FlowMsg::Info),
        })
        .one_button_request(ButtonRequest::from_num(br_code, br_name));

    // Cancelled
    let content_cancelled = TextScreen::new(
        Paragraph::new(&theme::TEXT_REGULAR, TR::send__sign_cancelled)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical()),
    )
    .with_header(Header::new(TR::words__title_done.into()).with_icon(theme::ICON_DONE, theme::GREY))
    .with_action_bar(ActionBar::new_timeout(
        Button::with_text(TR::instructions__continue_in_app.into()),
        TIMEOUT,
    ))
    .map(|_| Some(FlowMsg::Confirmed));

    let mut flow = SwipeFlow::new(&ConfirmOutput::Address)?;
    flow.add_page(&ConfirmOutput::Address, content_main)?
        .add_page(
            &ConfirmOutput::Menu,
            content_main_menu(
                address_title,
                address_menu_item,
                account_menu_item,
                cancel_menu_label,
            ),
        )?
        .add_page(
            &ConfirmOutput::AccountInfo,
            content_menu_info(
                account_title,
                account_subtitle,
                account_paragraphs.map_or_else(ParagraphVecShort::new, |p| p),
            ),
        )?
        .add_page(&ConfirmOutput::Cancel, content_cancel())?
        .add_page(&ConfirmOutput::Cancelled, content_cancelled)?;

    Ok(flow)
}
