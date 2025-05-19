use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        button_request::{ButtonRequest, ButtonRequestCode},
        component::{
            button_request::ButtonRequestExt,
            text::{
                op::OpTextLayout,
                paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs, VecExt},
            },
            ComponentExt, FormattedText, MsgMap, SendButtonRequest,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::{Direction, LinearPlacement},
        layout::util::RecoveryType,
    },
};

use super::super::{
    component::Button,
    firmware::{
        ActionBar, Header, ShortMenuVec, TextScreen, TextScreenMsg, VerticalMenu,
        VerticalMenuScreen, VerticalMenuScreenMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ContinueRecoveryBeforeShares {
    Main,
    Menu,
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ContinueRecoveryBetweenShares {
    Main,
    Menu,
    Cancel,
    RecoveryShare,
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ContinueRecoveryBetweenSharesAdvanced {
    Main,
    Menu,
    Cancel,
    RemainingShares,
}

impl FlowController for ContinueRecoveryBeforeShares {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Main, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Main, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, FlowMsg::Cancelled) => Self::Main.goto(),
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

impl FlowController for ContinueRecoveryBetweenShares {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Main, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Main, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, FlowMsg::Choice(0)) => Self::RecoveryShare.goto(),
            (Self::Menu, FlowMsg::Choice(1)) => Self::Cancel.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Main.goto(),
            (Self::Cancel, FlowMsg::Cancelled) => Self::Menu.goto(),
            (Self::Cancel, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            (Self::RecoveryShare, _) => Self::Menu.goto(),
            _ => self.do_nothing(),
        }
    }
}

impl FlowController for ContinueRecoveryBetweenSharesAdvanced {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Main, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Main, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, FlowMsg::Choice(0)) => Self::RemainingShares.goto(),
            (Self::Menu, FlowMsg::Choice(1)) => Self::Cancel.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Main.goto(),
            (Self::Cancel, FlowMsg::Cancelled) => Self::Menu.goto(),
            (Self::Cancel, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            (Self::RemainingShares, _) => Self::Menu.goto(),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_continue_recovery_homepage(
    text: TString<'static>,
    subtext: Option<TString<'static>>,
    recovery_type: RecoveryType,
    show_instructions: bool, // 1st screen of the recovery process
    remaining_shares: Option<(OpTextLayout<'static>, usize)>,
) -> Result<SwipeFlow, error::Error> {
    let is_multigroup_check = subtext.is_none();
    let (header, verb, cancel_btn, cancel_title, cancel_intro) = match recovery_type {
        RecoveryType::Normal if show_instructions => (
            Header::new(TR::recovery__title.into()).with_menu_button(),
            TR::buttons__continue,
            TR::recovery__title_cancel_recovery,
            TR::recovery__title,
            TR::recovery__wanna_cancel_recovery,
        ),
        RecoveryType::Normal => (
            Header::new(TR::words__title_done.into())
                .with_text_style(theme::label_title_confirm())
                .with_icon(theme::ICON_DONE, theme::GREEN_LIGHT)
                .with_menu_button(),
            TR::instructions__enter_next_share,
            TR::recovery__title_cancel_recovery,
            TR::recovery__title,
            TR::recovery__wanna_cancel_recovery,
        ),
        // 1st screen of the recovery process
        _ if show_instructions => (
            Header::new(TR::reset__check_wallet_backup_title.into()).with_menu_button(),
            TR::buttons__continue,
            TR::buttons__cancel,
            TR::reset__check_wallet_backup_title,
            TR::recovery__wanna_cancel_dry_run,
        ),
        _ => (
            // multi-group recovery check
            if is_multigroup_check {
                Header::new(TR::reset__check_wallet_backup_title.into()).with_menu_button()
            // single-group recovery check
            } else {
                Header::new(TR::words__title_done.into())
                    .with_text_style(theme::label_title_confirm())
                    .with_icon(theme::ICON_DONE, theme::GREEN_LIGHT)
                    .with_menu_button()
            },
            TR::buttons__continue,
            TR::buttons__cancel,
            TR::reset__check_wallet_backup_title,
            TR::recovery__wanna_cancel_dry_run,
        ),
    };

    let mut pars_main = ParagraphVecShort::new();
    if show_instructions {
        pars_main.add(Paragraph::new(
            &theme::TEXT_REGULAR,
            TR::recovery__enter_each_word,
        ));
    } else {
        pars_main.add(Paragraph::new(&theme::TEXT_REGULAR, text));
        if let Some(sub) = subtext {
            pars_main.add(Paragraph::new(&theme::TEXT_REGULAR, sub));
        }
    };

    let content_main = TextScreen::new(
        pars_main
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical())
            .with_spacing(24),
    )
    .with_header(header)
    .with_action_bar(ActionBar::new_single(Button::with_text(verb.into())))
    .repeated_button_request(ButtonRequest::new(
        ButtonRequestCode::RecoveryHomepage,
        "recovery".into(),
    ))
    .map(|msg| match msg {
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        TextScreenMsg::Menu => Some(FlowMsg::Info),
        _ => None,
    });

    let paragraphs_cancel = Paragraph::new(&theme::TEXT_REGULAR, cancel_intro)
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical());

    let content_cancel = TextScreen::new(paragraphs_cancel)
        .with_header(Header::new(cancel_title.into()))
        .with_action_bar(ActionBar::new_double(
            Button::with_icon(theme::ICON_CHEVRON_LEFT),
            Button::with_text(TR::buttons__cancel.into()).styled(theme::button_cancel()),
        ))
        .map(|msg| match msg {
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
            _ => None,
        })
        .repeated_button_request(ButtonRequest::new(
            ButtonRequestCode::ProtectCall,
            "abort_recovery".into(),
        ));

    match (show_instructions, remaining_shares) {
        (true, _) => flow_before_shares(content_main, cancel_btn.into()),
        (false, None) => flow_between_shares_simple(content_main, content_cancel),
        (false, Some((pages, n))) => {
            flow_between_shares_advanced(content_main, content_cancel, pages, n, cancel_btn.into())
        }
    }
}

fn flow_before_shares(
    content_main: MsgMap<
        SendButtonRequest<TextScreen<Paragraphs<ParagraphVecShort<'static>>>>,
        impl Fn(TextScreenMsg) -> Option<FlowMsg> + 'static,
    >,
    cancel_btn: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
    let content_menu = VerticalMenuScreen::new(VerticalMenu::<ShortMenuVec>::empty().with_item(
        Button::new_menu_item(cancel_btn, theme::menu_item_title_orange()),
    ))
    .with_header(Header::new(TString::empty()).with_close_button())
    .map(|msg| match msg {
        VerticalMenuScreenMsg::Selected(i) => Some(FlowMsg::Choice(i)),
        VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
        _ => None,
    });

    let mut res = SwipeFlow::new(&ContinueRecoveryBeforeShares::Main)?;
    res.add_page(&ContinueRecoveryBeforeShares::Main, content_main)?
        .add_page(&ContinueRecoveryBeforeShares::Menu, content_menu)?;
    Ok(res)
}

fn flow_between_shares_simple(
    content_main: MsgMap<
        SendButtonRequest<TextScreen<Paragraphs<ParagraphVecShort<'static>>>>,
        impl Fn(TextScreenMsg) -> Option<FlowMsg> + 'static,
    >,
    content_cancel: SendButtonRequest<
        MsgMap<
            TextScreen<Paragraphs<Paragraph<'static>>>,
            impl Fn(TextScreenMsg) -> Option<FlowMsg> + 'static,
        >,
    >,
) -> Result<SwipeFlow, error::Error> {
    let content_menu = VerticalMenuScreen::new(
        VerticalMenu::<ShortMenuVec>::empty()
            .with_item(Button::new_menu_item_with_subtext(
                TR::words__recovery_share.into(),
                theme::menu_item_title(),
                TR::buttons__more_info.into(),
                None,
            ))
            .with_item(Button::new_menu_item(
                TR::buttons__cancel.into(),
                theme::menu_item_title_orange(),
            )),
    )
    .with_header(Header::new(TR::recovery__title.into()).with_close_button())
    .map(|msg| match msg {
        VerticalMenuScreenMsg::Selected(i) => Some(FlowMsg::Choice(i)),
        VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
        _ => None,
    });

    let paragraphs_recovery_share = ParagraphVecShort::from_iter([
        Paragraph::new(&theme::TEXT_REGULAR, TR::reset__recovery_share_description)
            .with_bottom_padding(10),
        Paragraph::new(&theme::TEXT_REGULAR, TR::reset__recovery_share_number),
    ])
    .into_paragraphs()
    .with_placement(LinearPlacement::vertical());

    let content_recovery_share = TextScreen::new(paragraphs_recovery_share)
        .with_header(Header::new(TR::words__recovery_share.into()).with_close_button())
        .map(|_| Some(FlowMsg::Cancelled))
        .repeated_button_request(ButtonRequest::new(
            ButtonRequestCode::Other,
            "recovery_share".into(),
        ));

    let mut res = SwipeFlow::new(&ContinueRecoveryBetweenShares::Main)?;
    res.add_page(&ContinueRecoveryBetweenShares::Main, content_main)?
        .add_page(&ContinueRecoveryBetweenShares::Menu, content_menu)?
        .add_page(&ContinueRecoveryBetweenShares::Cancel, content_cancel)?
        .add_page(
            &ContinueRecoveryBetweenShares::RecoveryShare,
            content_recovery_share,
        )?;
    Ok(res)
}

fn flow_between_shares_advanced(
    content_main: MsgMap<
        SendButtonRequest<TextScreen<Paragraphs<ParagraphVecShort<'static>>>>,
        impl Fn(TextScreenMsg) -> Option<FlowMsg> + 'static,
    >,
    content_cancel: SendButtonRequest<
        MsgMap<
            TextScreen<Paragraphs<Paragraph<'static>>>,
            impl Fn(TextScreenMsg) -> Option<FlowMsg> + 'static,
        >,
    >,
    pages: OpTextLayout<'static>,
    n_remaining_shares: usize,
    cancel_btn: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
    let content_menu = VerticalMenuScreen::new(
        VerticalMenu::<ShortMenuVec>::empty()
            .with_item(Button::new_menu_item(
                TR::recovery__title_remaining_shares.into(),
                theme::menu_item_title(),
            ))
            .with_item(Button::new_menu_item(
                cancel_btn,
                theme::menu_item_title_orange(),
            )),
    )
    .with_header(Header::new(TString::empty()).with_close_button())
    .map(|msg| match msg {
        VerticalMenuScreenMsg::Selected(i) => Some(FlowMsg::Choice(i)),
        VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
        _ => None,
    });

    let content_remaining_shares = TextScreen::new(FormattedText::new(pages))
        .with_header(Header::new(TR::recovery__title_remaining_shares.into()).with_close_button())
        .map(|_| Some(FlowMsg::Cancelled))
        .repeated_button_request(ButtonRequest::new(
            ButtonRequestCode::Other,
            "show_shares".into(),
        ))
        .with_pages(move |_| n_remaining_shares);

    let mut res = SwipeFlow::new(&ContinueRecoveryBetweenSharesAdvanced::Main)?;
    res.add_page(&ContinueRecoveryBetweenSharesAdvanced::Main, content_main)?
        .add_page(&ContinueRecoveryBetweenSharesAdvanced::Menu, content_menu)?
        .add_page(
            &ContinueRecoveryBetweenSharesAdvanced::Cancel,
            content_cancel,
        )?
        .add_page(
            &ContinueRecoveryBetweenSharesAdvanced::RemainingShares,
            content_remaining_shares,
        )?;
    Ok(res)
}
