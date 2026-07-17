use core::sync::atomic::{AtomicBool, AtomicUsize, Ordering};

use super::super::component::{
    FidoCredential, Footer, Frame, Header, PagedVerticalMenu, PromptScreen, SwipeContent,
    VerticalMenu,
};
use super::super::theme;
use crate::error;
use crate::micropython::gc::Gc;
use crate::micropython::list::List;
use crate::strutil::TString;
use crate::translations::TR;
use crate::ui::component::paginated::Paginate as _;
use crate::ui::component::swipe_detect::SwipeSettings;
use crate::ui::component::text::paragraphs::{Paragraph, Paragraphs};
use crate::ui::component::EventCtx;
use crate::ui::flow::base::{Decision, DecisionBuilder as _};
use crate::ui::flow::{FlowController, FlowMsg, SwipeFlow, SwipePage};
use crate::ui::geometry::Direction;

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmFido {
    Intro,
    ChooseCredential,
    Details,
    Tap,
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

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Intro, Direction::Up) => Self::ChooseCredential.swipe(direction),
            (Self::ChooseCredential, Direction::Down) => Self::Intro.swipe(direction),
            (Self::Details, Direction::Up) => Self::Tap.swipe(direction),
            (Self::Tap, Direction::Down) => Self::Details.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (_, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Menu, FlowMsg::Cancelled) => {
                if single_cred() {
                    Self::Details.swipe_right()
                } else {
                    Self::Intro.swipe_right()
                }
            }
            (Self::ChooseCredential, FlowMsg::Choice(i)) => {
                CRED_SELECTED.store(i, Ordering::Relaxed);
                Self::Details.swipe_left()
            }
            (Self::Details, FlowMsg::Cancelled) => Self::ChooseCredential.swipe_right(),
            (Self::Tap, FlowMsg::Confirmed) => {
                self.return_msg(FlowMsg::Choice(CRED_SELECTED.load(Ordering::Relaxed)))
            }
            _ => self.do_nothing(),
        }
    }
}

fn footer_update_fn(
    content: &SwipeContent<SwipePage<PagedVerticalMenu<impl Fn(u16) -> TString<'static>>>>,
    ctx: &mut EventCtx,
    footer: &mut Footer,
) {
    footer.update_pager(ctx, content.inner().inner().pager());
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

    let header = Header::left_aligned(title).with_menu_button();
    let content_intro = Frame::with_header(
        header,
        SwipeContent::new(Paragraphs::new(Paragraph::new::<TString>(
            &theme::TEXT_MAIN_GREY_LIGHT,
            TR::fido__select_intro.into(),
        ))),
    )
    .with_swipeup_footer(None)
    .map_to_button_msg();

    // Closure to lazy-load the information on given page index.
    // Done like this to allow arbitrarily many pages without
    // the need of any allocation here in Rust.
    let label_fn = move |page_index: u16| {
        let account = unwrap!(accounts.get(page_index as usize));
        account
            .try_into()
            .unwrap_or_else(|_| TString::from_str("-"))
    };

    let header = Header::left_aligned(TR::fido__title_select_credential.into())
        .with_subtitle(TR::fido__title_for_authentication.into())
        .with_menu_button();
    let content_choose_credential = Frame::with_header(
        header,
        SwipeContent::new(SwipePage::vertical(PagedVerticalMenu::new(
            num_accounts,
            label_fn,
        ))),
    )
    .with_footer_page_hint(
        TR::fido__more_credentials.into(),
        TR::buttons__go_back.into(),
        TR::instructions__tap_to_continue.into(),
        TR::instructions__swipe_down.into(),
    )
    .register_footer_update_fn(footer_update_fn)
    .with_swipe(Direction::Down, SwipeSettings::Default)
    .with_vertical_pages()
    .map(super::util::map_to_choice);

    let get_account = move || {
        let current = CRED_SELECTED.load(Ordering::Relaxed);
        let account = unwrap!(accounts.get(current));
        account.try_into().unwrap_or_else(|_| TString::from_str(""))
    };
    let header = Header::left_aligned(TR::fido__title_credential_details.into());
    let header = if single_cred() {
        header.with_menu_button()
    } else {
        header.with_cancel_button()
    };
    let content_details = Frame::with_header(
        header,
        SwipeContent::new(FidoCredential::new(icon_name, app_name, get_account)),
    )
    .with_swipeup_footer(Some(title))
    .map_to_button_msg();

    let header = Header::left_aligned(title).with_menu_button();
    let content_tap = Frame::with_header(header, PromptScreen::new_tap_to_confirm())
        .with_footer(TR::instructions__tap_to_confirm.into(), None)
        .with_swipe(Direction::Down, SwipeSettings::Default)
        .map(super::util::map_to_confirm);

    let content_menu = Frame::with_header(
        Header::left_aligned("".into()).with_cancel_button(),
        VerticalMenu::empty().cancel_item(TR::buttons__cancel.into()),
    )
    .map(super::util::map_to_choice);

    let initial_page = if single_cred() {
        &ConfirmFido::Details
    } else {
        &ConfirmFido::Intro
    };
    let mut flow = SwipeFlow::new(initial_page)?;
    flow.add_page(&ConfirmFido::Intro, content_intro)?
        .add_page(&ConfirmFido::ChooseCredential, content_choose_credential)?
        .add_page(&ConfirmFido::Details, content_details)?
        .add_page(&ConfirmFido::Tap, content_tap)?
        .add_page(&ConfirmFido::Menu, content_menu)?;
    Ok(flow)
}
