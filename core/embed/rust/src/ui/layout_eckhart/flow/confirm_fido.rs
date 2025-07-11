use crate::{
    error,
    micropython::{gc::Gc, list::List},
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            base::ComponentExt,
            text::paragraphs::{Paragraph, ParagraphSource},
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
        ActionBar, FidoCredential, Header, LongMenuGc, ShortMenuVec, TextScreen, TextScreenMsg,
        VerticalMenu, VerticalMenuScreen, VerticalMenuScreenMsg,
    },
    theme::{self, gradient::Gradient},
};

use core::sync::atomic::{AtomicBool, AtomicUsize, Ordering};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmFido {
    Intro,
    ChooseCredential,
    Authenticate,
    Menu,
}

static CRED_SELECTED: AtomicUsize = AtomicUsize::new(0);
static SINGLE_CRED: AtomicBool = AtomicBool::new(false);
const EXTRA_PADDING: i16 = 6;

impl FlowController for ConfirmFido {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Intro, FlowMsg::Confirmed) => Self::ChooseCredential.goto(),
            (Self::ChooseCredential, FlowMsg::Choice(i)) => {
                CRED_SELECTED.store(i, Ordering::Relaxed);
                Self::Authenticate.goto()
            }
            (_, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Authenticate, FlowMsg::Cancelled) => {
                if single_cred() {
                    self.return_msg(FlowMsg::Cancelled)
                } else {
                    Self::ChooseCredential.goto()
                }
            }
            (Self::Authenticate, FlowMsg::Confirmed) => {
                self.return_msg(FlowMsg::Choice(CRED_SELECTED.load(Ordering::Relaxed)))
            }
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Menu, FlowMsg::Cancelled) => {
                if single_cred() {
                    Self::Authenticate.goto()
                } else {
                    Self::Intro.goto()
                }
            }
            _ => self.do_nothing(),
        }
    }
}

fn single_cred() -> bool {
    SINGLE_CRED.load(Ordering::Relaxed)
}

pub fn new_confirm_fido(
    title: TString<'static>,
    app_name: TString<'static>,
    icon_name: Option<TString<'static>>,
    accounts: Gc<List>,
) -> Result<SwipeFlow, error::Error> {
    let num_accounts = accounts.len();
    SINGLE_CRED.store(num_accounts <= 1, Ordering::Relaxed);
    CRED_SELECTED.store(0, Ordering::Relaxed);

    // Intro screen
    let content_intro = TextScreen::new(
        Paragraph::new::<TString>(&theme::TEXT_REGULAR, TR::fido__select_intro.into())
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical()),
    )
    .with_header(Header::new(title).with_menu_button())
    .with_action_bar(ActionBar::new_single(Button::with_text(
        TR::buttons__continue.into(),
    )))
    .map(|msg| match msg {
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        TextScreenMsg::Menu => Some(FlowMsg::Info),
        _ => None,
    });

    // Choose credential screen
    let mut credentials = VerticalMenu::<LongMenuGc>::empty();
    for i in 0..num_accounts {
        let account = unwrap!(accounts.get(i));
        let label = account
            .try_into()
            .unwrap_or_else(|_| TString::from_str("-"));
        credentials.item(Button::new_single_line_menu_item(
            label,
            theme::menu_item_title(),
        ));
    }
    let content_choose_credential = VerticalMenuScreen::new(credentials)
        .with_header(Header::new(TR::fido__title_select_credential.into()))
        .map(|msg| match msg {
            VerticalMenuScreenMsg::Selected(i) => Some(FlowMsg::Choice(i)),
            VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
            VerticalMenuScreenMsg::Menu => Some(FlowMsg::Info),
            _ => None,
        });

    // Authenticate screen
    let get_account = move || {
        let current = CRED_SELECTED.load(Ordering::Relaxed);
        let account = unwrap!(accounts.get(current));
        account.try_into().unwrap_or_else(|_| TString::from_str(""))
    };
    let auth_header = if single_cred() {
        Header::new(title)
    } else {
        Header::new(TR::fido__title_credential_details.into()).with_close_button()
    };
    let auth_action_bar = if single_cred() {
        ActionBar::new_cancel_confirm()
    } else {
        ActionBar::new_single(
            Button::with_text(TR::words__authenticate.into())
                .styled(theme::button_confirm())
                .with_gradient(Gradient::SignGreen),
        )
    };

    let content_authenticate =
        TextScreen::new(FidoCredential::new(icon_name, app_name, get_account))
            .with_header(auth_header)
            .with_action_bar(auth_action_bar)
            .map(|msg| match msg {
                TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
                TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
                TextScreenMsg::Menu => Some(FlowMsg::Info),
            });

    // Menu screen
    let content_menu = VerticalMenuScreen::new(VerticalMenu::<ShortMenuVec>::empty().with_item(
        Button::new_menu_item(TR::buttons__cancel.into(), theme::menu_item_title_orange()),
    ))
    .with_header(Header::new(title).with_close_button())
    .map(|msg| match msg {
        VerticalMenuScreenMsg::Selected(0) => Some(FlowMsg::Choice(0)),
        VerticalMenuScreenMsg::Menu => Some(FlowMsg::Info),
        VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
        _ => None,
    });

    let initial_page = if single_cred() {
        &ConfirmFido::Authenticate
    } else {
        &ConfirmFido::Intro
    };
    let mut flow = SwipeFlow::new(initial_page)?;
    flow.add_page(&ConfirmFido::Intro, content_intro)?
        .add_page(&ConfirmFido::ChooseCredential, content_choose_credential)?
        .add_page(&ConfirmFido::Authenticate, content_authenticate)?
        .add_page(&ConfirmFido::Menu, content_menu)?;
    Ok(flow)
}
