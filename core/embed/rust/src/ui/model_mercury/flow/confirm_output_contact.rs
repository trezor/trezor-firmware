use crate::ui::button_request::{ButtonRequest, ButtonRequestCode};
use crate::ui::component::text::paragraphs::ParagraphSource;
use crate::ui::component::ButtonRequestExt;
use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeSettings, text::paragraphs::ParagraphVecShort, ComponentExt,
        },
        flow::{
            base::{Decision, DecisionBuilder},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::Direction,
        model_mercury::{
            component::{
                Frame, FrameMsg, PromptMsg, PromptScreen, SwipeContent, VerticalMenu,
                VerticalMenuChoiceMsg,
            },
            theme,
        },
    },
};

use super::{ConfirmBlobParams, ShowInfoParams};

#[derive(Copy, Clone, PartialEq, Eq)]
enum ConfirmOutputContact {
    Contact,
    Amount,
    Menu,
    AddressInfo,
    Confirm,
}
impl FlowController for ConfirmOutputContact {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Contact | Self::Amount, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Contact, Direction::Up) => Self::Amount.swipe(direction),

            (Self::Menu, Direction::Right) => Self::Contact.swipe(direction),
            (Self::AddressInfo, Direction::Right) => Self::Menu.swipe(direction),

            (Self::Amount, Direction::Down) => Self::Contact.swipe(direction),
            (Self::Amount, Direction::Up) => self.return_msg(FlowMsg::Confirmed),

            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Contact, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Amount, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Choice(0)) => Self::AddressInfo.goto(),
            (Self::Menu, FlowMsg::Choice(1)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Menu, FlowMsg::Cancelled) => Self::Contact.swipe_right(),
            (Self::AddressInfo, FlowMsg::Cancelled) => Self::Menu.goto(),
            _ => self.do_nothing(),
        }
    }
}
pub fn new_confirm_output_contact(
    title: TString<'static>,
    subtitle: TString<'static>,
    paragraphs: ParagraphVecShort<'static>,
    address_params: ShowInfoParams,
    amount_params: ConfirmBlobParams,
) -> Result<SwipeFlow, error::Error> {
    let paragraphs = paragraphs.into_paragraphs();
    let br_code = ButtonRequestCode::ConfirmOutput as u16;
    let br_name = "confirm_output".into();

    // Contact
    let content_contact = Frame::left_aligned(title, SwipeContent::new(paragraphs))
        .with_swipe(Direction::Up, SwipeSettings::default())
        .with_swipe(Direction::Left, SwipeSettings::default())
        .with_subtitle(subtitle)
        .with_menu_button()
        .with_footer(TR::instructions__swipe_up.into(), None)
        .map(move |msg| match msg {
            FrameMsg::Button(_) => Some(FlowMsg::Info),
            FrameMsg::Content(_) => Some(FlowMsg::Confirmed),
        })
        .one_button_request(ButtonRequest::from_num(br_code, br_name));

    // Amount
    let content_amount = amount_params
        .into_layout()?
        .one_button_request(ButtonRequest::from_num(br_code, br_name));

    // Address info
    let content_address = address_params.into_layout()?;

    // Menu
    let content_menu = VerticalMenu::empty()
        .item(theme::ICON_CHEVRON_RIGHT, TR::words__address.into())
        .danger(theme::ICON_CANCEL, TR::send__cancel_sign.into());
    let content_menu = Frame::left_aligned(TString::empty(), content_menu)
        .with_cancel_button()
        .with_swipe(Direction::Right, SwipeSettings::immediate())
        .map(move |msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

    // Hold to confirm
    let content_confirm = Frame::left_aligned(
        TR::send__sign_transaction.into(),
        SwipeContent::new(PromptScreen::new_hold_to_confirm()),
    )
    .with_menu_button()
    .with_footer(TR::instructions__hold_to_sign.into(), None)
    .with_swipe(Direction::Down, SwipeSettings::default())
    .with_swipe(Direction::Left, SwipeSettings::default())
    .map(|msg| match msg {
        FrameMsg::Content(PromptMsg::Confirmed) => Some(FlowMsg::Confirmed),
        FrameMsg::Button(_) => Some(FlowMsg::Info),
        _ => None,
    });

    let res = SwipeFlow::new(&ConfirmOutputContact::Contact)?
        .with_page(&ConfirmOutputContact::Contact, content_contact)?
        .with_page(&ConfirmOutputContact::Amount, content_amount)?
        .with_page(&ConfirmOutputContact::Menu, content_menu)?
        .with_page(&ConfirmOutputContact::AddressInfo, content_address)?
        .with_page(&ConfirmOutputContact::Confirm, content_confirm)?;
    Ok(res)
}
