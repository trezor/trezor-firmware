use core::cmp::Ordering;

use heapless::Vec;

use super::component::{
    AddressDetails, ButtonActions, ButtonDetails, ButtonLayout, ButtonPage, ChoiceControls,
    CoinJoinProgress, ConfirmHomescreen, Flow, FlowPages, Frame, Homescreen, Lockscreen, MenuNav,
    NumberInput, Page, PassphraseEntry, PinEntry, Progress, ScrollableFrame, ShareWords,
    SimpleChoice, WordlistEntry, WordlistType, SIMPLE_CHOICE_MAX_LENGTH,
};
use super::{constant, fonts, theme, UICaesar};
use crate::io::BinaryData;
use crate::maybe_trace::MaybeTrace;
use crate::micropython::buffer::StrBuffer;
use crate::micropython::gc::Gc;
use crate::micropython::iter::IterBuf;
use crate::micropython::list::List;
use crate::micropython::{util, Error, Obj};
use crate::strutil::TString;
use crate::translations::TR;
use crate::ui::component::text::op::OpTextLayout;
use crate::ui::component::text::paragraphs::{
    Checklist, Paragraph, ParagraphSource, ParagraphVecLong, ParagraphVecShort, Paragraphs, VecExt,
};
use crate::ui::component::text::TextStyle;
use crate::ui::component::{
    Component, ComponentExt, Empty, FlowMsg, FormattedText, LineBreaking, Never, PageMsg, Paginate,
    Timeout,
};
use crate::ui::layout::menu_item_intent::MenuItemIntent;
use crate::ui::layout::obj::{LayoutMaybeTrace, LayoutObj, RootComponent};
use crate::ui::layout::util::{ConfirmValueParams, PropsList, RecoveryType};
use crate::ui::notification::Notification;
use crate::ui::ui_firmware::{
    DeviceMenuParams, FirmwareUI, SelectMenuItem, MAX_CHECKLIST_ITEMS, MAX_GROUP_SHARE_LINES,
    MAX_MENU_ITEMS, MAX_WORD_QUIZ_ITEMS,
};
use crate::ui::{geometry, ModelUI};

impl FirmwareUI for UICaesar {
    fn confirm_action(
        title: TString<'static>,
        action: Option<TString<'static>>,
        description: Option<TString<'static>>,
        _subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        _cancel: bool,
        verb_cancel: Option<TString<'static>>,
        hold: bool,
        _hold_danger: bool,
        reverse: bool,
        _prompt_screen: bool,
        _prompt_title: Option<TString<'static>>,
        external_menu: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = {
            let action = action.unwrap_or("".into());
            let description = description.unwrap_or("".into());
            let mut paragraphs = ParagraphVecShort::new();
            if !reverse {
                paragraphs
                    .add(Paragraph::new(&theme::TEXT_BOLD, action))
                    .add(Paragraph::new(&theme::TEXT_NORMAL, description));
            } else {
                paragraphs
                    .add(Paragraph::new(&theme::TEXT_NORMAL, description))
                    .add(Paragraph::new(&theme::TEXT_BOLD, action));
            }
            paragraphs.into_paragraphs()
        };

        content_in_button_page(
            title,
            paragraphs,
            verb.unwrap_or(TString::empty()),
            verb_cancel,
            hold,
            external_menu.then_some(MenuNav::Menu),
            false,
        )
    }

    fn confirm_address(
        title: TString<'static>,
        address: Obj,
        address_label: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        info_button: bool,
        chunkify: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        let verb = verb.unwrap_or(TR::buttons__confirm.into());
        let address: TString = address.try_into()?;

        let address_ops = move || {
            let mut ops = OpTextLayout::new(theme::TEXT_MONO_DATA);
            if let Some(label) = address_label {
                // NOTE: need to explicitly turn off the chunkification before rendering the
                // address label (for some reason it does not help to turn it off after
                // rendering the chunks)
                if chunkify {
                    ops.add_chunkify_text(None);
                }
                // the label is a text, breaking only at whitespace
                ops.add_line_breaking(LineBreaking::BreakAtWhitespace)
                    .add_text_with_font(label, fonts::FONT_NORMAL)
                    .add_newline()
                    .add_line_breaking(theme::TEXT_MONO_DATA.line_breaking);
            }
            if chunkify {
                // Chunkifying the address into smaller pieces when requested
                ops.add_chunkify_text(Some((theme::MONO_CHUNKS, 2)));
            }
            ops.add_text_with_font(address, fonts::FONT_MONO);
            FormattedText::new(ops).vertically_centered()
        };

        // The info is in the context menu, opened by the left button. Without
        // it, the left button cancels.
        let menu_nav = if info_button {
            MenuNav::Menu
        } else {
            MenuNav::Close
        };
        let content = ButtonPage::new(address_ops(), theme::BG)
            .with_menu_nav(menu_nav)
            .with_confirm_btn(Some(ButtonDetails::text(verb)));
        let frame = ScrollableFrame::new(content).with_title(title);
        LayoutObj::new(frame)
    }

    fn confirm_trade(
        _title: TString<'static>,
        _subtitle: TString<'static>,
        _sell_amount: Option<TString<'static>>,
        _buy_amount: TString<'static>,
        _back_button: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn confirm_value(
        title: TString<'static>,
        value: Obj,
        description: Option<TString<'static>>,
        is_data: bool,
        extra: Option<TString<'static>>,
        _subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
        info: bool,
        hold: bool,
        chunkify: bool,
        _page_counter: bool,
        _prompt_screen: bool,
        _cancel: bool,
        back_button: bool,
        _footer: Option<(TString<'static>, bool)>,
        external_menu: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = ConfirmValueParams {
            description: description.unwrap_or("".into()),
            extra: extra.unwrap_or("".into()),
            value: value.try_into()?,
            font: if chunkify {
                // Chunkifying the address into smaller pieces when requested
                &theme::TEXT_MONO_ADDRESS_CHUNKS
            } else if is_data {
                &theme::TEXT_MONO_DATA
            } else {
                &theme::TEXT_NORMAL
            },
            description_font: &theme::TEXT_BOLD,
            extra_font: &theme::TEXT_NORMAL,
        }
        .into_paragraphs();

        content_in_button_page(
            title,
            paragraphs,
            verb.unwrap_or(TR::buttons__confirm.into()),
            verb_cancel,
            hold,
            // `info` is a menu with choices how to continue the flow
            if external_menu {
                Some(MenuNav::Menu)
            } else if info {
                Some(MenuNav::ChoiceMenu)
            } else {
                None
            },
            back_button,
        )
    }

    fn confirm_value_intro(
        _title: TString<'static>,
        _value: Obj,
        _subtitle: Option<TString<'static>>,
        _verb: Option<TString<'static>>,
        _verb_cancel: Option<TString<'static>>,
        _verb_view_all: Option<TString<'static>>,
        _hold: bool,
        _chunkify: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        Err::<Gc<LayoutObj>, Error>(Error::NotImplementedError)
    }

    fn confirm_homescreen(
        title: TString<'static>,
        image: BinaryData<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(ConfirmHomescreen::new(title, image));
        Ok(layout)
    }

    fn confirm_coinjoin(
        _max_rounds: TString<'static>,
        _max_feerate: TString<'static>,
        _max_coordinator_fee_pct: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        // Composed in Python from `confirm_properties`.
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn confirm_emphasized(
        _title: TString<'static>,
        _items: Obj,
        _verb: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    #[cfg(feature = "universal_fw")]
    fn confirm_fido(
        title: TString<'static>,
        app_name: TString<'static>,
        _icon: Option<TString<'static>>,
        accounts: Gc<List>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        // Cache the page count so that we can move `accounts` into the closure.
        let page_count = accounts.len();

        // Closure to lazy-load the information on given page index.
        // Done like this to allow arbitrarily many pages without
        // the need of any allocation here in Rust.
        let get_page = move |page_index| {
            let account_obj = unwrap!(accounts.get(page_index));
            let account = TString::try_from(account_obj).unwrap_or_else(|_| TString::empty());

            let (btn_layout, btn_actions) = if page_count == 1 {
                // There is only one page
                (
                    ButtonLayout::cancel_none_text(TR::buttons__confirm.into()),
                    ButtonActions::cancel_none_confirm(),
                )
            } else if page_index == 0 {
                // First page
                (
                    ButtonLayout::cancel_armed_arrow(TR::buttons__select.into()),
                    ButtonActions::cancel_confirm_next(),
                )
            } else if page_index == page_count - 1 {
                // Last page
                (
                    ButtonLayout::arrow_armed_none(TR::buttons__select.into()),
                    ButtonActions::prev_confirm_none(),
                )
            } else {
                // Page in the middle
                (
                    ButtonLayout::arrow_armed_arrow(TR::buttons__select.into()),
                    ButtonActions::prev_confirm_next(),
                )
            };

            let mut ops = OpTextLayout::new(theme::TEXT_NORMAL);
            ops.add_newline()
                .add_text_with_font(app_name, fonts::FONT_NORMAL)
                .add_newline()
                .add_text_with_font(account, fonts::FONT_BOLD);
            let formatted = FormattedText::new(ops);

            Page::new(btn_layout, btn_actions, formatted)
        };

        let pages = FlowPages::new(get_page, page_count);
        // Returning the page index in case of confirmation.
        let obj = RootComponent::new(
            Flow::new(pages)
                .with_common_title(title)
                .with_return_confirmed_index(),
        );
        Ok(obj)
    }

    fn confirm_firmware_update(
        description: TString<'static>,
        _fingerprint: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        // The fingerprint is shown in the context menu.
        let paragraphs = Paragraph::new(&theme::TEXT_NORMAL, description).into_paragraphs();
        let content = ButtonPage::new(paragraphs, theme::BG)
            .with_menu_nav(MenuNav::Menu)
            .with_confirm_btn(Some(ButtonDetails::text(TR::buttons__install.into())));
        let frame = ScrollableFrame::new(content).with_title(TR::firmware_update__title.into());
        Ok(RootComponent::new(frame))
    }

    fn confirm_modify_fee(
        _title: TString<'static>,
        _sign: i32,
        _user_fee_change: TString<'static>,
        _total_fee_new: TString<'static>,
        _fee_rate_amount: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        // Composed in Python from `confirm_properties`.
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn confirm_modify_output(
        sign: i32,
        amount_change: TString<'static>,
        amount_new: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let description = if sign < 0 {
            TR::modify_amount__decrease_amount
        } else {
            TR::modify_amount__increase_amount
        };

        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_NORMAL, description),
            Paragraph::new(&theme::TEXT_MONO, amount_change).break_after(),
            Paragraph::new(&theme::TEXT_BOLD, TR::modify_amount__new_amount),
            Paragraph::new(&theme::TEXT_MONO, amount_new),
        ]);

        content_in_button_page(
            TR::modify_amount__title.into(),
            paragraphs,
            TR::buttons__confirm.into(),
            // going back to the address
            Some("^".into()),
            false,
            None,
            false,
        )
    }

    fn confirm_more(
        _title: TString<'static>,
        _button: TString<'static>,
        _button_style_confirm: bool,
        _hold: bool,
        _items: Obj,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        // Long content is paginated in a single screen on this model.
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn confirm_properties(
        title: TString<'static>,
        _subtitle: Option<TString<'static>>,
        items: Obj,
        hold: bool,
        verb: Option<TString<'static>>,
        external_menu: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = PropsList::new(items)?;

        let button_text = verb.unwrap_or(if hold {
            TR::buttons__hold_to_confirm.into()
        } else {
            TR::buttons__confirm.into()
        });

        content_in_button_page(
            title,
            paragraphs.into_paragraphs(),
            button_text,
            Some("".into()),
            hold,
            external_menu.then_some(MenuNav::Menu),
            false,
        )
    }

    fn confirm_reset_device(recovery: bool) -> Result<impl LayoutMaybeTrace, Error> {
        let (title, button) = if recovery {
            (
                TR::recovery__title_recover.into(),
                TR::reset__button_recover.into(),
            )
        } else {
            (
                TR::reset__title_create_wallet.into(),
                TR::reset__button_create.into(),
            )
        };
        let mut ops = OpTextLayout::new(theme::TEXT_NORMAL);
        ops.add_text_with_font(TR::reset__by_continuing, fonts::FONT_NORMAL)
            .add_next_page()
            .add_text_with_font(TR::reset__more_info_at, fonts::FONT_NORMAL)
            .add_newline()
            .add_text_with_font(TR::reset__tos_link, fonts::FONT_BOLD);
        let formatted = FormattedText::new(ops).vertically_centered();

        content_in_button_page(
            title,
            formatted,
            button,
            Some("".into()),
            false,
            None,
            false,
        )
    }

    fn confirm_summary(
        amount: Option<TString<'static>>,
        amount_label: Option<TString<'static>>,
        fee: TString<'static>,
        fee_label: TString<'static>,
        title: Option<TString<'static>>,
        account_items: Option<Obj>,
        _account_title: Option<TString<'static>>,
        extra_items: Option<Obj>,
        _extra_title: Option<TString<'static>>,
        _verb_cancel: Option<TString<'static>>,
        back_button: bool,
        external_menu: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        if account_items.is_some() || extra_items.is_some() {
            // The information is shown in the context menu on this model.
            return Err(Error::NotImplementedError);
        }

        let mut ops = OpTextLayout::new(theme::TEXT_MONO);
        let mut has_amount = false;
        if let Some(amount) = amount {
            if let Some(amount_label) = amount_label {
                has_amount = true;
                ops.add_text_with_font(amount_label, fonts::FONT_BOLD);
                if !amount_label.is_empty() && !amount.is_empty() {
                    ops.add_newline();
                }
                ops.add_text_with_font(amount, fonts::FONT_MONO);
            }
        }
        if !fee_label.is_empty() || !fee.is_empty() {
            if has_amount {
                ops.add_newline();
            }
            ops.add_newline()
                .add_text_with_font(fee_label, fonts::FONT_BOLD)
                .add_newline()
                .add_text_with_font(fee, fonts::FONT_MONO);
        }

        // The info is in the context menu, opened by the left button. Without
        // it, the left button cancels.
        let mut content = ButtonPage::new(FormattedText::new(ops), theme::BG).with_confirm_btn(
            Some(ButtonDetails::text(TR::buttons__hold_to_confirm.into()).with_default_duration()),
        );
        if external_menu {
            content = content.with_menu_nav(MenuNav::Menu);
            if back_button {
                content = content.with_back_on_first_page();
            }
        } else {
            content = content.with_menu_nav(MenuNav::Close);
        }
        let mut frame = ScrollableFrame::new(content);
        if let Some(title) = title {
            frame = frame.with_title(title);
        }
        Ok(RootComponent::new(frame))
    }

    fn confirm_with_info(
        title: TString<'static>,
        subtitle: Option<TString<'static>>,
        items: Obj,
        verb: TString<'static>,
        verb_info: Option<TString<'static>>,
        _verb_cancel: Option<TString<'static>>,
        external_menu: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        let mut paragraphs = ParagraphVecShort::new();

        if let Some(subtitle) = subtitle {
            paragraphs.add(Paragraph::new(&theme::TEXT_BOLD, subtitle));
        }

        for para in IterBuf::new().try_iterate(items)? {
            let [text, is_data]: [Obj; 2] = util::iter_into_array(para)?;
            let is_data = is_data.try_into()?;
            let style: &TextStyle = if is_data {
                &theme::TEXT_MONO_DATA
            } else {
                &theme::TEXT_NORMAL
            };
            let text: TString = text.try_into()?;
            paragraphs.add(Paragraph::new(style, text));
            if paragraphs.is_full() {
                break;
            }
        }

        // The info, or the choice to show more (`verb_info`), is in the context
        // menu, opened by the left button. Without it, the left button cancels.
        let menu_nav = if external_menu {
            MenuNav::Menu
        } else if verb_info.is_some_and(|verb_info| !verb_info.is_empty()) {
            MenuNav::ChoiceMenu
        } else {
            MenuNav::Close
        };
        let confirm_btn = if verb == TString::Str(DOWN_ARROW) {
            ButtonDetails::scroll_down_wide()
        } else {
            ButtonDetails::text(verb)
        };
        let content = ButtonPage::new(paragraphs.into_paragraphs(), theme::BG)
            .with_menu_nav(menu_nav)
            .with_confirm_btn(Some(confirm_btn));
        LayoutObj::new(ScrollableFrame::new(content).with_title(title))
    }

    fn check_homescreen_format(image: BinaryData, _accept_toif: bool) -> bool {
        super::component::check_homescreen_format(image)
    }

    fn continue_recovery_homepage(
        text: TString<'static>,
        _subtext: Option<TString<'static>>,
        button: Option<TString<'static>>,
        recovery_type: RecoveryType,
        show_instructions: bool,
        _remaining_shares: Option<crate::micropython::obj::Obj>,
    ) -> Result<Gc<LayoutObj>, Error> {
        let mut paragraphs = ParagraphVecShort::new();
        let button = button.unwrap_or(TString::empty());
        paragraphs.add(Paragraph::new(&theme::TEXT_NORMAL, text));
        if show_instructions {
            paragraphs
                .add(Paragraph::new(
                    &theme::TEXT_NORMAL,
                    TR::recovery__enter_each_word,
                ))
                .add(Paragraph::new(
                    &theme::TEXT_NORMAL,
                    TR::recovery__cursor_will_change,
                ));
        }

        let title = match recovery_type {
            RecoveryType::DryRun => TR::recovery__title_dry_run,
            RecoveryType::UnlockRepeatedBackup => TR::recovery__title_dry_run,
            _ => TR::recovery__title,
        };

        let layout = content_in_button_page(
            title.into(),
            paragraphs.into_paragraphs(),
            button,
            Some("".into()),
            false,
            None,
            false,
        )?;
        LayoutObj::new_root(layout)
    }

    fn flow_confirm_set_new_code(_is_wipe_code: bool) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn flow_get_address(
        _address: TString<'static>,
        _title: TString<'static>,
        _subtitle: Option<TString<'static>>,
        _description: Option<TString<'static>>,
        _hint: Option<TString<'static>>,
        _chunkify: bool,
        _address_qr: TString<'static>,
        _case_sensitive: bool,
        _account: Option<TString<'static>>,
        _path: Option<TString<'static>>,
        _xpubs: Obj,
        _br_code: u16,
        _br_name: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn flow_get_pubkey(
        _pubkey: TString<'static>,
        _title: TString<'static>,
        _subtitle: Option<TString<'static>>,
        _hint: Option<TString<'static>>,
        _pubkey_qr: TString<'static>,
        _account: Option<TString<'static>>,
        _path: Option<TString<'static>>,
        _br_code: u16,
        _br_name: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn multiple_pages_texts(
        title: TString<'static>,
        verb: TString<'static>,
        items: Gc<List>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        // Each item on its own page.
        let mut ops = OpTextLayout::new(theme::TEXT_NORMAL);
        for (i, item) in IterBuf::new().try_iterate(items.into())?.enumerate() {
            if i > 0 {
                ops.add_next_page();
            }
            ops.add_text_with_font(TString::try_from(item)?, fonts::FONT_NORMAL);
        }
        let formatted = FormattedText::new(ops).vertically_centered();
        content_in_button_page(title, formatted, verb, Some("".into()), false, None, false)
    }

    fn prompt_backup() -> Result<impl LayoutMaybeTrace, Error> {
        let mut ops = OpTextLayout::new(theme::TEXT_NORMAL);
        ops.add_text_with_font(TR::backup__new_wallet_created, fonts::FONT_NORMAL)
            .add_newline()
            .add_text_with_font(TR::backup__it_should_be_backed_up_now, fonts::FONT_NORMAL)
            .add_next_page()
            .add_text_with_font(TR::backup__recover_anytime, fonts::FONT_NORMAL);
        let formatted = FormattedText::new(ops).vertically_centered();

        // Skipping the backup is in the context menu.
        let content = ButtonPage::new(formatted, theme::BG)
            .with_menu_nav(MenuNav::ChoiceMenu)
            .with_confirm_btn(Some(ButtonDetails::text(TR::buttons__back_up.into())));
        let frame = ScrollableFrame::new(content).with_page_titles([
            TR::words__title_success.into(),
            TR::backup__title_backup_wallet.into(),
        ]);
        Ok(RootComponent::new(frame))
    }

    fn request_bip39(
        prompt: TString<'static>,
        prefill_word: TString<'static>,
        can_go_back: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(
            Frame::new(
                prompt,
                prefill_word
                    .map(|s| WordlistEntry::prefilled_word(s, WordlistType::Bip39, can_go_back)),
            )
            .with_title_centered(),
        );
        Ok(layout)
    }

    fn request_slip39(
        prompt: TString<'static>,
        prefill_word: TString<'static>,
        can_go_back: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(
            Frame::new(
                prompt,
                prefill_word
                    .map(|s| WordlistEntry::prefilled_word(s, WordlistType::Slip39, can_go_back)),
            )
            .with_title_centered(),
        );
        Ok(layout)
    }

    fn request_number(
        title: TString<'static>,
        count: u32,
        min_count: u32,
        max_count: u32,
        _description: Option<TString<'static>>,
        _more_info_callback: Option<impl Fn(u32) -> TString<'static> + 'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(
            Frame::new(title, NumberInput::new(min_count, max_count, count)).with_title_centered(),
        );
        Ok(layout)
    }

    fn request_duration(
        _title: TString<'static>,
        _duration_ms: u32,
        _min_ms: u32,
        _max_ms: u32,
        _description: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn request_pin(
        prompt: TString<'static>,
        attempts: TString<'static>,
        _allow_cancel: bool,
        _wrong_pin: bool,
        _last_attempt: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(PinEntry::new(prompt, attempts));
        Ok(layout)
    }

    fn request_passphrase(
        prompt: TString<'static>,
        _prompt_empty: TString<'static>,
        max_len: usize,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(
            Frame::new(prompt, PassphraseEntry::new(max_len)).with_title_centered(),
        );
        Ok(layout)
    }

    fn request_string(
        _prompt: TString<'static>,
        _max_len: usize,
        _allow_empty: bool,
        _prefill: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn select_menu(
        items: heapless::Vec<SelectMenuItem, MAX_MENU_ITEMS>,
        current: usize,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let labels: heapless::Vec<TString<'static>, SIMPLE_CHOICE_MAX_LENGTH> =
            items.iter().map(|item| item.text).collect();
        // the entry's intent is not rendered, it is only traced for the tests
        let danger_items = items
            .iter()
            .map(|item| item.intent == MenuItemIntent::Danger)
            .collect();
        // Returning the index of the selected menu item. The select text is not
        // used, the menu buttons show an arrow glyph instead.
        let layout = RootComponent::new(
            SimpleChoice::new(labels, ChoiceControls::Cancellable, TString::empty())
                .with_menu_buttons(danger_items)
                .with_initial_page_counter(current)
                .with_show_incomplete()
                .with_return_index()
                .with_ignore_cancelled(),
        );
        Ok(layout)
    }

    fn select_word(
        _title: TString<'static>,
        description: TString<'static>,
        words: [TString<'static>; MAX_WORD_QUIZ_ITEMS],
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let words: Vec<TString<'static>, SIMPLE_CHOICE_MAX_LENGTH> = Vec::from_iter(words);
        // Returning the index of the selected word, not the word itself
        let layout = RootComponent::new(
            Frame::new(
                description,
                SimpleChoice::new(words, ChoiceControls::Carousel, TR::buttons__select.into())
                    .with_show_incomplete()
                    .with_return_index(),
            )
            .with_title_centered(),
        );
        Ok(layout)
    }

    fn select_word_count(recovery_type: RecoveryType) -> Result<impl LayoutMaybeTrace, Error> {
        let title: TString = TR::word_count__title.into();
        let choices: Vec<TString<'static>, SIMPLE_CHOICE_MAX_LENGTH> = {
            let nums: &[&str] = if matches!(recovery_type, RecoveryType::UnlockRepeatedBackup) {
                &["20", "33"]
            } else {
                &["12", "18", "20", "24", "33"]
            };
            nums.iter().map(|&num| num.into()).collect()
        };
        let layout = RootComponent::new(
            Frame::new(
                title,
                SimpleChoice::new(
                    choices,
                    ChoiceControls::Cancellable,
                    TR::buttons__select.into(),
                ),
            )
            .with_title_centered(),
        );
        Ok(layout)
    }

    fn set_brightness(_current_brightness: Option<u8>) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn show_address_details(
        _qr_title: TString<'static>,
        address: TString<'static>,
        case_sensitive: bool,
        _details_title: TString<'static>,
        _account: Option<(TString<'static>, TString<'static>)>,
        _path: Option<(TString<'static>, TString<'static>)>,
        _xpubs: Obj,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        // Only the QR code, the account information has its own menu item.
        let layout = RootComponent::new(AddressDetails::new(address, case_sensitive)?);
        Ok(layout)
    }

    fn show_checklist(
        _title: TString<'static>,
        button: TString<'static>,
        active: usize,
        items: [TString<'static>; MAX_CHECKLIST_ITEMS],
        back_button: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut paragraphs = ParagraphVecLong::new();
        for (i, item) in items.into_iter().enumerate() {
            let style = match i.cmp(&active) {
                Ordering::Less => &theme::TEXT_NORMAL,
                Ordering::Equal => &theme::TEXT_BOLD,
                Ordering::Greater => &theme::TEXT_NORMAL,
            };
            paragraphs.add(Paragraph::new(style, item));
        }
        let confirm_btn = Some(ButtonDetails::text(button));
        // The left button (only present when `back_button` is set) emits
        // `PageMsg::Cancelled`; interpret it as going back. Going back is the
        // only way out of the checklist -- interrupting the flow is not
        // possible.
        let cancel_btn = back_button.then(ButtonDetails::up_arrow_icon);
        let map_fn: fn(PageMsg<Never>) -> Option<FlowMsg> = |msg| match msg {
            PageMsg::Cancelled => Some(FlowMsg::Back),
            PageMsg::Confirmed => Some(FlowMsg::Confirmed),
            _ => None,
        };

        let layout = RootComponent::new(
            ButtonPage::new(
                Checklist::from_paragraphs(
                    theme::ICON_ARROW_RIGHT_FAT,
                    theme::ICON_TICK_FAT,
                    active,
                    paragraphs
                        .into_paragraphs()
                        .with_spacing(theme::CHECKLIST_SPACING),
                )
                .with_check_width(theme::CHECKLIST_CHECK_WIDTH)
                .with_current_offset(theme::CHECKLIST_CURRENT_OFFSET),
                theme::BG,
            )
            .with_confirm_btn(confirm_btn)
            .with_cancel_btn(cancel_btn)
            .map(map_fn),
        );
        Ok(layout)
    }

    fn show_danger(
        title: TString<'static>,
        description: TString<'static>,
        _value: TString<'static>,
        _menu_title: Option<TString<'static>>,
        _verb_cancel: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let get_page = move |page_index| {
            assert!(page_index == 0);

            let btn_layout = ButtonLayout::cancel_none_text(TR::buttons__continue.into());
            let btn_actions = ButtonActions::cancel_none_confirm();
            let mut ops = OpTextLayout::new(theme::TEXT_NORMAL);
            ops.add_alignment(geometry::Alignment::Center);
            if !title.is_empty() {
                ops.add_text_with_font(title, fonts::FONT_BOLD_UPPER);
                if !description.is_empty() {
                    ops.add_newline();
                }
            }
            if !description.is_empty() {
                ops.add_text_with_font(description, fonts::FONT_NORMAL);
            }
            let formatted = FormattedText::new(ops).vertically_centered();
            Page::new(btn_layout, btn_actions, formatted)
        };
        let pages = FlowPages::new(get_page, 1);
        let layout = RootComponent::new(Flow::new(pages));
        Ok(layout)
    }

    fn show_error(
        _title: TString<'static>,
        _button: TString<'static>,
        _description: TString<'static>,
        _allow_cancel: bool,
        _time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        Err::<Gc<LayoutObj>, Error>(Error::NotImplementedError)
    }

    fn show_group_share_success(
        lines: [TString<'static>; MAX_GROUP_SHARE_LINES],
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_MONO, lines[0]),
            Paragraph::new(&theme::TEXT_BOLD, lines[1]),
            Paragraph::new(&theme::TEXT_MONO, lines[2]),
            Paragraph::new(&theme::TEXT_BOLD, lines[3]),
        ]);
        content_in_button_page(
            "".into(),
            paragraphs,
            TR::buttons__continue.into(),
            None,
            false,
            None,
            false,
        )
    }

    fn show_homescreen(
        label: TString<'static>,
        notification: Option<Notification>,
        lockable: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let loader_description = lockable.then_some(TR::progress__locking_device.into());
        let layout = RootComponent::new(Homescreen::new(label, notification, loader_description));
        Ok(layout)
    }

    fn show_device_menu(_params: DeviceMenuParams) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn show_pairing_device_name(
        _description: StrBuffer,
        _device_name: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    #[cfg(feature = "ble")]
    fn show_ble_pairing_code(
        _title: TString<'static>,
        _description: TString<'static>,
        _code: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    #[cfg(feature = "ble")]
    fn wait_ble_host_confirmation() -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn show_thp_pairing_code(
        title: TString<'static>,
        description: TString<'static>,
        code: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Self::confirm_action(
            title,
            Some(code),
            Some(description),
            None,
            None,
            true,
            None,
            false,
            false,
            false,
            false,
            None,
            false,
        )
    }

    fn confirm_thp_pairing(
        _title: TString<'static>,
        _description: (StrBuffer, Obj),
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn show_info(
        title: TString<'static>,
        description: TString<'static>,
        _button: Option<(TString<'static>, bool)>,
        time_ms: u32,
        external_menu: bool, // TODO: will eventually replace the internal menu
    ) -> Result<Gc<LayoutObj>, Error> {
        if external_menu {
            return Err(Error::NotImplementedError);
        }
        let content = Frame::new(
            title,
            Paragraphs::new([Paragraph::new(&theme::TEXT_NORMAL, description)]),
        );
        let obj = if time_ms == 0 {
            // No timer, used when we only want to draw the dialog once and
            // then throw away the layout object.
            LayoutObj::new(content)?
        } else {
            // Timeout.
            let timeout = Timeout::new(time_ms);
            LayoutObj::new((timeout, content.map(|_| None)))?
        };
        Ok(obj)
    }

    fn show_info_with_cancel(
        _title: TString<'static>,
        _items: Obj,
        _horizontal: bool,
        _chunkify: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn show_lockscreen(
        label: TString<'static>,
        bootscreen: bool,
        coinjoin_authorized: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(Lockscreen::new(label, bootscreen, coinjoin_authorized));
        Ok(layout)
    }

    fn show_mismatch(title: TString<'static>) -> Result<impl LayoutMaybeTrace, Error> {
        let get_page = move |page_index| {
            assert!(page_index == 0);

            let btn_layout = ButtonLayout::arrow_none_text(TR::buttons__quit.into());
            let btn_actions = ButtonActions::cancel_none_confirm();
            let mut ops = OpTextLayout::new(theme::TEXT_NORMAL);
            ops.add_text_with_font(title, fonts::FONT_BOLD_UPPER)
                .add_newline()
                .add_newline_half()
                .add_text_with_font(TR::addr_mismatch__contact_support_at, fonts::FONT_NORMAL)
                .add_newline()
                .add_text_with_font(TR::addr_mismatch__support_url, fonts::FONT_BOLD);
            let formatted = FormattedText::new(ops);
            Page::new(btn_layout, btn_actions, formatted)
        };
        let pages = FlowPages::new(get_page, 1);

        let obj = RootComponent::new(Flow::new(pages));
        Ok(obj)
    }

    fn show_progress(
        description: TString<'static>,
        indeterminate: bool,
        title: Option<TString<'static>>,
        _danger: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut progress = Progress::new(indeterminate, description);
        if let Some(title) = title {
            progress = progress.with_title(title);
        };

        let layout = RootComponent::new(progress);
        Ok(layout)
    }

    fn show_progress_coinjoin(
        title: TString<'static>,
        indeterminate: bool,
        time_ms: u32,
        skip_first_paint: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        let progress = CoinJoinProgress::new(title, indeterminate);
        let obj = if time_ms > 0 && indeterminate {
            let timeout = Timeout::new(time_ms);
            LayoutObj::new((timeout, progress.map(|_msg| None)))?
        } else {
            LayoutObj::new(progress)?
        };
        if skip_first_paint {
            obj.skip_first_paint();
        }
        Ok(obj)
    }

    fn show_properties(
        title: TString<'static>,
        _subtitle: Option<TString<'static>>,
        value: Obj,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut paragraphs = ParagraphVecLong::new();
        if Obj::is_str(value) {
            // Display string value using monospace font
            add_paragraphs(&mut paragraphs, None, Some(value.try_into()?), true);
        } else {
            for para in IterBuf::new().try_iterate(value)? {
                let [key, value, _is_data]: [Obj; 3] = util::iter_into_array(para)?;
                add_paragraphs(
                    &mut paragraphs,
                    key.try_into_option()?,
                    value.try_into_option()?,
                    false,
                );
            }
        }

        // Opened from the context menu, closed by the left button.
        let page = ButtonPage::new(paragraphs.into_paragraphs(), theme::BG)
            .with_menu_nav(MenuNav::Close)
            .with_confirm_btn(None);

        let mut frame = ScrollableFrame::new(page);
        if !title.is_empty() {
            frame = frame.with_title(title);
        }

        Ok(RootComponent::new(frame))
    }

    fn show_share_words(
        words: heapless::Vec<TString<'static>, 33>,
        _title: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let cancel_btn = Some(ButtonDetails::up_arrow_icon());
        let confirm_btn =
            Some(ButtonDetails::text(TR::buttons__hold_to_confirm.into()).with_default_duration());

        let layout = RootComponent::new(
            ButtonPage::new(ShareWords::new(words), theme::BG)
                .with_cancel_btn(cancel_btn)
                .with_confirm_btn(confirm_btn),
        );
        Ok(layout)
    }

    fn show_share_words_extended(
        _words: heapless::Vec<TString<'static>, 33>,
        _subtitle: Option<TString<'static>>,
        _instructions: Obj,
        _instructions_verb: Option<TString<'static>>,
        _text_footer: Option<TString<'static>>,
        _text_confirm: TString<'static>,
        _text_check: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn show_remaining_shares(_pages_iterable: Obj) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn show_simple(
        text: TString<'static>,
        _title: Option<TString<'static>>,
        _button: Option<TString<'static>>,
    ) -> Result<Gc<LayoutObj>, Error> {
        let paragraph = Paragraph::new(&theme::TEXT_NORMAL, text).centered();
        let content = Paragraphs::new([paragraph]);
        let obj = LayoutObj::new(content)?;
        Ok(obj)
    }

    fn show_success(
        _title: TString<'static>,
        _button: TString<'static>,
        _description: TString<'static>,
        _allow_cancel: bool,
        _time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        Err::<Gc<LayoutObj>, Error>(Error::NotImplementedError)
    }

    fn show_warning(
        title: Option<TString<'static>>,
        button: TString<'static>,
        value: TString<'static>,
        description: TString<'static>,
        _allow_cancel: bool,
        danger: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        if danger && title.is_none() {
            // Disallow showing "dangerous" warning with no header.
            return Err(Error::ValueError(c"Non-empty title is required"));
        }
        let get_page = move |page_index| {
            assert!(page_index == 0);

            let btn_layout = ButtonLayout::none_armed_none(button);
            let btn_actions = ButtonActions::none_confirm_none();
            let mut ops = OpTextLayout::new(theme::TEXT_NORMAL);
            ops.add_alignment(geometry::Alignment::Center);
            if !value.is_empty() {
                ops.add_text_with_font(value, fonts::FONT_BOLD_UPPER);
                if !description.is_empty() {
                    ops.add_newline();
                }
            }
            if !description.is_empty() {
                ops.add_text_with_font(description, fonts::FONT_NORMAL);
            }
            let formatted = FormattedText::new(ops).vertically_centered();
            Page::new(btn_layout, btn_actions, formatted)
        };
        let pages = FlowPages::new(get_page, 1);
        let obj = LayoutObj::new(Flow::new(pages))?;
        Ok(obj)
    }

    fn confirm_cancel() -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn tutorial() -> Result<impl LayoutMaybeTrace, Error> {
        const PAGE_COUNT: usize = 7;

        let get_page = move |page_index| {
            // Lazy-loaded list of screens to show, with custom content,
            // buttons and actions triggered by these buttons.
            // Cancelling the first screen will point to the last one,
            // which asks for confirmation whether user wants to
            // really cancel the tutorial.
            match page_index {
                // title, text, btn_layout, btn_actions
                0 => tutorial_screen(
                    TR::tutorial__title_hello.into(),
                    TR::tutorial__welcome_press_right,
                    ButtonLayout::cancel_none_arrow(),
                    ButtonActions::last_none_next(),
                ),
                1 => tutorial_screen(
                    "".into(),
                    TR::tutorial__use_trezor,
                    ButtonLayout::arrow_none_arrow(),
                    ButtonActions::prev_none_next(),
                ),
                2 => tutorial_screen(
                    TR::instructions__hold_to_confirm.into(),
                    TR::tutorial__press_and_hold,
                    ButtonLayout::arrow_none_htc(TR::buttons__hold_to_confirm.into()),
                    ButtonActions::prev_none_next(),
                ),
                3 => tutorial_screen(
                    TR::tutorial__title_screen_scroll.into(),
                    TR::tutorial__scroll_down,
                    ButtonLayout::arrow_none_text(TR::buttons__continue.into()),
                    ButtonActions::prev_none_next(),
                ),
                4 => tutorial_screen(
                    TR::buttons__confirm.into(),
                    TR::tutorial__middle_click,
                    ButtonLayout::none_armed_none(TR::buttons__confirm.into()),
                    ButtonActions::none_next_none(),
                ),
                5 => tutorial_screen(
                    TR::tutorial__title_tutorial_complete.into(),
                    TR::tutorial__ready_to_use,
                    ButtonLayout::text_none_text(
                        TR::buttons__again.into(),
                        TR::buttons__continue.into(),
                    ),
                    ButtonActions::beginning_none_confirm(),
                ),
                6 => tutorial_screen(
                    TR::tutorial__title_skip.into(),
                    TR::tutorial__sure_you_want_skip,
                    ButtonLayout::arrow_none_text(TR::buttons__skip.into()),
                    ButtonActions::beginning_none_cancel(),
                ),
                _ => unreachable!(),
            }
        };

        let pages = FlowPages::new(get_page, PAGE_COUNT);

        // Setting the ignore-second-button to mimic all the Choice pages, to teach user
        // that they should really press both buttons at the same time to achieve
        // middle-click.
        let layout = RootComponent::new(
            Flow::new(pages)
                .with_scrollbar(false)
                .with_ignore_second_button_ms(constant::IGNORE_OTHER_BTN_MS),
        );
        Ok(layout)
    }
}

/// Text of the confirm button showing a wide down arrow instead.
const DOWN_ARROW: &str = "V";

/// Function to create and call a `ButtonPage` dialog based on paginable content
/// (e.g. `Paragraphs` or `FormattedText`).
/// Has optional title (supply empty `TString` for that) and hold-to-confirm
/// functionality.
///
/// With `menu`, the left button opens the context menu, and with `back_button`
/// also "Shift" + right button on the first page goes back to the previous
/// screen. Otherwise, an empty `verb_cancel` puts a cross cancelling the flow
/// on the left.
fn content_in_button_page<T: Component + Paginate + MaybeTrace + 'static>(
    title: TString<'static>,
    content: T,
    verb: TString<'static>,
    verb_cancel: Option<TString<'static>>,
    hold: bool,
    menu: Option<MenuNav>,
    back_button: bool,
) -> Result<impl LayoutMaybeTrace, Error> {
    // Right button - down arrow, text or nothing.
    // Optional HoldToConfirm
    let mut confirm_btn = if verb.is_empty() {
        None
    } else if verb == TString::Str(DOWN_ARROW) {
        Some(ButtonDetails::scroll_down_wide())
    } else {
        Some(ButtonDetails::text(verb))
    };
    if hold {
        confirm_btn = confirm_btn.map(|btn| btn.with_default_duration());
    }

    let mut content = ButtonPage::new(content, theme::BG).with_confirm_btn(confirm_btn);
    if let Some(menu) = menu {
        content = content.with_menu_nav(menu);
        if back_button {
            content = content.with_back_on_first_page();
        }
    } else if verb_cancel.is_some_and(|verb_cancel| verb_cancel.is_empty()) {
        content = content.with_menu_nav(MenuNav::Close);
    } else {
        // Left button - back arrow, text or nothing.
        content = content.with_cancel_btn(verb_cancel.map(ButtonDetails::from_text_possible_icon));
    }

    let mut frame = ScrollableFrame::new(content);
    if !title.is_empty() {
        frame = frame.with_title(title);
    }

    Ok(RootComponent::new(frame))
}

/// General pattern of most tutorial screens.
/// (title, text, btn_layout, btn_actions, text_y_offset)
fn tutorial_screen(
    title: TString<'static>,
    text: TR,
    btn_layout: ButtonLayout,
    btn_actions: ButtonActions,
) -> Page {
    let mut ops = OpTextLayout::new(theme::TEXT_NORMAL);
    ops.add_text_with_font(text, fonts::FONT_NORMAL);
    let formatted = FormattedText::new(ops).vertically_centered();
    Page::new(btn_layout, btn_actions, formatted).with_title(title)
}

fn add_paragraphs<'a>(
    paragraphs: &mut ParagraphVecLong<'a>,
    key: Option<TString<'a>>,
    value: Option<TString<'a>>,
    is_data: bool,
) {
    if let Some(key) = key {
        if value.is_some() {
            // Decreasing the margin between key and value (default is 5 px, we use 2 px)
            // (this enables 4 lines - 2 key:value pairs - on the same screen)
            paragraphs.add(
                Paragraph::new(&theme::TEXT_BOLD, key)
                    .no_break()
                    .with_bottom_padding(2),
            );
        } else {
            paragraphs.add(Paragraph::new(&theme::TEXT_BOLD, key));
        }
    }
    if let Some(value) = value {
        let style = if is_data {
            &theme::TEXT_MONO_DATA
        } else {
            &theme::TEXT_MONO
        };
        paragraphs.add(Paragraph::new(style, value));
    }
}
