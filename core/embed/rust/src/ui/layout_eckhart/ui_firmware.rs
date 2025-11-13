use core::cmp::Ordering;

use crate::{
    error::Error,
    io::BinaryData,
    micropython::{buffer::StrBuffer, gc::Gc, iter::IterBuf, list::List, obj::Obj, util},
    storage,
    strutil::TString,
    time::Duration,
    translations::TR,
    ui::{
        component::{
            text::{
                op::OpTextLayout,
                paragraphs::{
                    Checklist, Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs, VecExt,
                },
                TextStyle,
            },
            ComponentExt as _, Empty, FormattedText, Timeout,
        },
        flow::FlowMsg,
        geometry::{Alignment, LinearPlacement, Offset},
        layout::{
            obj::{LayoutMaybeTrace, LayoutObj, RootComponent},
            util::{ConfirmValueParams, ContentType, PropsList, RecoveryType, StrOrBytes},
        },
        ui_firmware::{
            FirmwareUI, MAX_CHECKLIST_ITEMS, MAX_GROUP_SHARE_LINES, MAX_MENU_ITEMS,
            MAX_PAIRED_DEVICES, MAX_WORD_QUIZ_ITEMS,
        },
        ModelUI,
    },
    util::interpolate,
};

use trezor_structs::ArchivedTrezorUiEnum;

#[cfg(feature = "ble")]
use crate::ui::component::{BLEHandler, BLEHandlerMode};

use super::{
    component::Button,
    firmware::{
        ActionBar, Bip39Input, ConfirmHomescreen, DeviceMenuScreen, DurationInput, Header,
        HeaderMsg, Hint, Homescreen, LabelInput, MnemonicKeyboard, PinKeyboard, ProgressScreen,
        SelectWordCountScreen, SelectWordScreen, SetBrightnessScreen, ShortMenuVec, Slip39Input,
        StringKeyboard, TextScreen, TextScreenMsg, ValueInputScreen, VerticalMenu,
        VerticalMenuScreen, VerticalMenuScreenMsg,
    },
    flow, fonts,
    theme::{
        self,
        firmware::{button_actionbar_danger, button_confirm},
        gradient::Gradient,
    },
    UIEckhart,
};

impl FirmwareUI for UIEckhart {
    fn confirm_action(
        title: TString<'static>,
        action: Option<TString<'static>>,
        description: Option<TString<'static>>,
        subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        _verb_cancel: Option<TString<'static>>,
        hold: bool,
        hold_danger: bool,
        reverse: bool,
        _prompt_screen: bool,
        _prompt_title: Option<TString<'static>>,
        _external_menu: bool, // TODO: will eventually replace the internal menu
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = {
            let action = action.unwrap_or("".into());
            let description = description.unwrap_or("".into());
            let mut paragraphs = ParagraphVecShort::new();
            if !reverse {
                paragraphs
                    .add(Paragraph::new(&theme::TEXT_REGULAR, action))
                    .add(Paragraph::new(&theme::TEXT_REGULAR, description));
            } else {
                paragraphs
                    .add(Paragraph::new(&theme::TEXT_REGULAR, description))
                    .add(Paragraph::new(&theme::TEXT_REGULAR, action));
            }
            paragraphs.into_paragraphs().with_placement(
                LinearPlacement::vertical().with_spacing(theme::TEXT_VERTICAL_SPACING),
            )
        };

        let right_button = match (hold, verb) {
            (true, verb) => {
                let verb = verb.unwrap_or(TR::buttons__hold_to_confirm.into());
                let (style, gradient) = if hold_danger {
                    (button_actionbar_danger(), theme::Gradient::Alert)
                } else {
                    (button_confirm(), theme::Gradient::SignGreen)
                };
                Button::with_text(verb)
                    .with_long_press(theme::CONFIRM_HOLD_DURATION)
                    .with_long_press_danger(hold_danger)
                    .with_gradient(gradient)
                    .styled(style)
            }
            (false, Some(verb)) => Button::with_text(verb),
            (false, None) => {
                Button::with_text(TR::buttons__confirm.into()).styled(button_confirm())
            }
        };

        let mut screen = TextScreen::new(paragraphs)
            .with_header(Header::new(title))
            .with_action_bar(ActionBar::new_double(
                Button::with_icon(theme::ICON_CROSS),
                right_button,
            ));
        if let Some(subtitle) = subtitle {
            screen = screen.with_hint(Hint::new_instruction(subtitle, None));
        }
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn confirm_address(
        _title: TString<'static>,
        _address: Obj,
        _address_label: Option<TString<'static>>,
        _verb: Option<TString<'static>>,
        _info_button: bool,
        _chunkify: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        Err::<Gc<LayoutObj>, Error>(Error::NotImplementedError)
    }

    fn confirm_homescreen(
        title: TString<'static>,
        image: BinaryData<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let screen = ConfirmHomescreen::new(title, image)?;
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn confirm_coinjoin(
        max_rounds: TString<'static>,
        max_feerate: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_REGULAR, TR::coinjoin__max_rounds)
                .with_bottom_padding(theme::PROP_INNER_SPACING)
                .no_break(),
            Paragraph::new(&theme::TEXT_MONO_LIGHT, max_rounds)
                .with_bottom_padding(theme::PROPS_SPACING),
            Paragraph::new(&theme::TEXT_REGULAR, TR::coinjoin__max_mining_fee)
                .with_bottom_padding(theme::PROP_INNER_SPACING)
                .no_break(),
            Paragraph::new(&theme::TEXT_MONO_LIGHT, max_feerate),
        ])
        .with_placement(LinearPlacement::vertical());

        let screen = TextScreen::new(paragraphs)
            .with_header(Header::new(TR::coinjoin__title.into()))
            .with_action_bar(ActionBar::new_cancel_confirm());
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn confirm_emphasized(
        title: TString<'static>,
        items: Obj,
        verb: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let font = fonts::FONT_SATOSHI_REGULAR_38;
        let text_style = theme::firmware::TEXT_REGULAR;
        let mut ops = OpTextLayout::new(text_style);

        for item in IterBuf::new().try_iterate(items)? {
            if item.is_str() {
                ops.add_text_with_font(TString::try_from(item)?, font);
            } else {
                let [emphasis, text]: [Obj; 2] = util::iter_into_array(item)?;
                let text: TString = text.try_into()?;
                if emphasis.try_into()? {
                    ops.add_color(theme::WHITE)
                        .add_text_with_font(text, font)
                        .add_color(text_style.text_color);
                } else {
                    ops.add_text_with_font(text, font);
                }
            }
        }
        let text = FormattedText::new(ops);
        let right_button = if let Some(verb) = verb {
            Button::with_text(verb)
        } else {
            Button::with_text(TR::buttons__confirm.into()).styled(button_confirm())
        };
        let action_bar = ActionBar::new_double(Button::with_icon(theme::ICON_CROSS), right_button);
        let screen = TextScreen::new(text)
            .with_header(Header::new(title))
            .with_action_bar(action_bar);
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn confirm_fido(
        title: TString<'static>,
        app_name: TString<'static>,
        icon: Option<TString<'static>>,
        accounts: Gc<List>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        #[cfg(feature = "universal_fw")]
        return flow::confirm_fido::new_confirm_fido(title, app_name, icon, accounts);
        #[cfg(not(feature = "universal_fw"))]
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn confirm_firmware_update(
        description: TString<'static>,
        fingerprint: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let flow =
            flow::confirm_firmware_update::new_confirm_firmware_update(description, fingerprint)?;
        Ok(flow)
    }

    fn confirm_modify_fee(
        title: TString<'static>,
        sign: i32,
        user_fee_change: TString<'static>,
        total_fee_new: TString<'static>,
        _fee_rate_amount: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let (description, change, total_label, info_hint) = match sign {
            s if s < 0 => (
                Some(TR::modify_fee__decrease_fee),
                user_fee_change,
                TR::modify_fee__new_transaction_fee,
                None,
            ),
            s if s > 0 => (
                Some(TR::modify_fee__increase_fee),
                user_fee_change,
                TR::modify_fee__new_transaction_fee,
                None,
            ),
            _ => (
                None,
                TString::empty(),
                TR::modify_fee__transaction_fee,
                Some(TR::modify_fee__no_change.into()),
            ),
        };

        let mut paragraphs = ParagraphVecShort::new();
        if let Some(description) = description {
            paragraphs
                .add(
                    Paragraph::new(&theme::TEXT_SMALL_LIGHT, description)
                        .with_bottom_padding(theme::PROP_INNER_SPACING),
                )
                .add(
                    Paragraph::new(&theme::TEXT_MONO_EXTRA_LIGHT, change)
                        .with_bottom_padding(theme::PROPS_SPACING),
                );
        }
        paragraphs
            .add(
                Paragraph::new(&theme::TEXT_SMALL_LIGHT, total_label)
                    .with_bottom_padding(theme::PROP_INNER_SPACING),
            )
            .add(Paragraph::new(&theme::TEXT_MONO_EXTRA_LIGHT, total_fee_new));

        let flow = flow::new_confirm_with_menu(
            title,
            None,
            paragraphs
                .into_paragraphs()
                .with_placement(LinearPlacement::vertical()),
            info_hint,
            None,
            false,
            Some(TR::confirm_total__title_fee.into()),
            None,
        )?;
        Ok(flow)
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
            Paragraph::new(&theme::TEXT_SMALL_LIGHT, description)
                .with_bottom_padding(theme::PROP_INNER_SPACING)
                .no_break(),
            Paragraph::new(&theme::TEXT_MONO_EXTRA_LIGHT, amount_change)
                .with_bottom_padding(theme::PROPS_SPACING),
            Paragraph::new(&theme::TEXT_SMALL_LIGHT, TR::modify_amount__new_amount)
                .with_bottom_padding(theme::PROP_INNER_SPACING)
                .no_break(),
            Paragraph::new(&theme::TEXT_MONO_EXTRA_LIGHT, amount_new),
        ])
        .with_placement(LinearPlacement::vertical());

        let layout = RootComponent::new(
            TextScreen::new(paragraphs)
                .with_header(Header::new(TR::modify_amount__title.into()))
                .with_action_bar(ActionBar::new_cancel_confirm()),
        );
        Ok(layout)
    }

    fn confirm_more(
        _title: TString<'static>,
        _button: TString<'static>,
        _button_style_confirm: bool,
        _hold: bool,
        _items: Obj,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn confirm_reset_device(recovery: bool) -> Result<impl LayoutMaybeTrace, Error> {
        let flow = flow::confirm_reset::new_confirm_reset(recovery)?;
        Ok(flow)
    }

    fn confirm_summary(
        amount: Option<TString<'static>>,
        amount_label: Option<TString<'static>>,
        fee: TString<'static>,
        fee_label: TString<'static>,
        title: Option<TString<'static>>,
        account_items: Option<Obj>,
        account_title: Option<TString<'static>>,
        extra_items: Option<Obj>,
        extra_title: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
        back_button: bool,
        _external_menu: bool, // TODO: will eventually replace the internal menu
    ) -> Result<impl LayoutMaybeTrace, Error> {
        // collect available info
        let account_paragraphs = if let Some(items) = account_items {
            Some(PropsList::new(items)?)
        } else {
            None
        };
        let extra_paragraphs = if let Some(items) = extra_items {
            Some(PropsList::new(items)?)
        } else {
            None
        };

        let flow = flow::new_confirm_summary(
            title.unwrap_or(TString::empty()),
            amount,
            amount_label,
            fee,
            fee_label,
            account_title,
            account_paragraphs,
            extra_title,
            extra_paragraphs,
            verb_cancel,
            back_button,
        )?;
        Ok(flow)
    }

    fn confirm_properties(
        title: TString<'static>,
        _subtitle: Option<TString<'static>>,
        items: Obj,
        hold: bool,
        verb: Option<TString<'static>>,
        _external_menu: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = PropsList::new_styled(
            items,
            &theme::TEXT_SMALL_LIGHT,
            &theme::TEXT_MONO_MEDIUM_LIGHT,
            &theme::TEXT_MONO_MEDIUM_LIGHT_DATA,
            theme::PROP_INNER_SPACING,
            theme::PROPS_SPACING,
        )?
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical());

        let flow =
            flow::new_confirm_with_menu(title, None, paragraphs, None, verb, hold, None, None)?;
        Ok(flow)
    }

    fn confirm_trade(
        title: TString<'static>,
        subtitle: TString<'static>,
        sell_amount: Option<TString<'static>>,
        buy_amount: TString<'static>,
        back_button: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let font = fonts::FONT_SATOSHI_REGULAR_38;
        let mut ops = OpTextLayout::new(theme::firmware::TEXT_REGULAR);
        ops.add_offset(Offset::y(16))
            .add_color(theme::RED)
            .add_text_with_font(sell_amount.unwrap_or(TString::empty()), font)
            .add_offset(Offset::y(44))
            .add_newline()
            .add_color(theme::GREEN_LIME)
            .add_text_with_font(buy_amount, font);
        let screen = TextScreen::new(FormattedText::new(ops))
            .with_subtitle(subtitle)
            .with_header(Header::new(title).with_menu_button())
            .with_action_bar(ActionBar::new_double(
                Button::with_icon(if back_button {
                    theme::ICON_CHEVRON_UP
                } else {
                    theme::ICON_CLOSE
                }),
                Button::with_text(TR::buttons__continue.into()),
            ))
            .map(move |msg| match msg {
                TextScreenMsg::Cancelled => Some(if back_button {
                    FlowMsg::Back
                } else {
                    FlowMsg::Cancelled
                }),
                TextScreenMsg::Menu => Some(FlowMsg::Info),
                TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            });
        flow::util::single_page(screen)
    }

    fn confirm_value(
        title: TString<'static>,
        value: Obj,
        description: Option<TString<'static>>,
        is_data: bool,
        extra: Option<TString<'static>>,
        subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        _verb_cancel: Option<TString<'static>>,
        info: bool,
        hold: bool,
        chunkify: bool,
        page_counter: bool,
        _prompt_screen: bool,
        cancel: bool,
        warning_footer: Option<TString<'static>>,
        external_menu: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        if info && external_menu {
            return Err(Error::NotImplementedError);
        }

        let paragraphs = ConfirmValueParams {
            description: description.unwrap_or("".into()),
            extra: extra.unwrap_or("".into()),
            value: if value != Obj::const_none() {
                value.try_into()?
            } else {
                StrOrBytes::Str("".into())
            },
            font: if chunkify {
                &theme::TEXT_MONO_ADDRESS_CHUNKS
            } else if is_data {
                &theme::TEXT_MONO_ADDRESS
            } else {
                &theme::TEXT_MONO_MEDIUM_LIGHT
            },
            description_font: &theme::TEXT_SMALL,
            extra_font: &theme::TEXT_SMALL,
        }
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical())
        .with_spacing(theme::PROP_INNER_SPACING);

        let mut right_button = if hold {
            let verb = verb.unwrap_or(TR::buttons__hold_to_confirm.into());
            Button::with_text(verb)
                .with_long_press(theme::CONFIRM_HOLD_DURATION)
                .styled(button_confirm())
        } else if let Some(verb) = verb {
            Button::with_text(verb)
        } else {
            Button::with_text(TR::buttons__confirm.into()).styled(button_confirm())
        };
        if warning_footer.is_some() {
            right_button = right_button
                .styled(theme::button_actionbar_danger())
                .with_gradient(Gradient::Alert);
        }
        let header = if info {
            Header::new(title)
                .with_right_button(Button::with_icon(theme::ICON_INFO), HeaderMsg::Menu)
        } else if external_menu {
            Header::new(title)
                .with_right_button(Button::with_icon(theme::ICON_MENU), HeaderMsg::Menu)
        } else {
            Header::new(title)
        };

        let action_bar = if cancel {
            ActionBar::new_double(Button::with_icon(theme::ICON_CROSS), right_button)
        } else {
            ActionBar::new_single(right_button)
        };

        let mut screen = TextScreen::new(paragraphs)
            .with_header(header)
            .with_subtitle(subtitle.unwrap_or(TString::empty()))
            .with_action_bar(action_bar)
            .with_external_menu(external_menu);
        if page_counter {
            screen = screen.with_hint(Hint::new_page_counter())
        } else if let Some(warning_footer) = warning_footer {
            screen = screen.with_hint(Hint::new_warning_caution(warning_footer));
        }
        LayoutObj::new(screen)
    }

    fn confirm_value_intro(
        title: TString<'static>,
        value: Obj,
        subtitle: Option<TString<'static>>,
        verb: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
        hold: bool,
        chunkify: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        let flow = flow::new_confirm_value_intro(
            title,
            subtitle,
            value,
            TR::buttons__view_all_data.into(),
            verb_cancel,
            verb,
            hold,
            chunkify,
        )?;

        LayoutObj::new_root(flow)
    }

    fn confirm_with_info(
        title: TString<'static>,
        subtitle: Option<TString<'static>>,
        items: Obj,
        verb: TString<'static>,
        verb_info: TString<'static>,
        _verb_cancel: Option<TString<'static>>,
        _external_menu: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut paragraphs = ParagraphVecShort::new();

        for para in IterBuf::new().try_iterate(items)? {
            let [text, is_data]: [Obj; 2] = util::iter_into_array(para)?;
            let is_data = is_data.try_into()?;
            let style: &TextStyle = if is_data {
                &theme::TEXT_MONO_LIGHT
            } else {
                &theme::TEXT_SMALL_LIGHT
            };
            let text: TString = text.try_into()?;
            paragraphs.add(Paragraph::new(style, text));
            if paragraphs.is_full() {
                break;
            }
        }

        let flow = flow::new_confirm_with_menu(
            title,
            subtitle,
            paragraphs
                .into_paragraphs()
                .with_placement(LinearPlacement::vertical())
                .with_spacing(theme::TEXT_VERTICAL_SPACING),
            None,
            Some(verb),
            false,
            Some(verb_info),
            None,
        )?;
        Ok(flow)
    }

    fn check_homescreen_format(image: BinaryData, _accept_toif: bool) -> bool {
        super::firmware::check_homescreen_format(image)
    }

    fn continue_recovery_homepage(
        text: TString<'static>,
        subtext: Option<TString<'static>>,
        _button: Option<TString<'static>>,
        recovery_type: RecoveryType,
        show_instructions: bool,
        remaining_shares: Option<Obj>,
    ) -> Result<Gc<LayoutObj>, Error> {
        let shares_layout = if let Some(pages_obj) = remaining_shares {
            let mut op_layout = OpTextLayout::new(theme::TEXT_SMALL);
            let mut iter_buf = IterBuf::new();
            let mut n_pages = 0;
            for page in iter_buf.try_iterate(pages_obj)? {
                if n_pages > 0 {
                    op_layout.add_next_page();
                }
                n_pages += 1;
                let [title, description]: [TString; 2] = util::iter_into_array(page)?;
                op_layout
                    .add_line_spacing(3)
                    .add_color(theme::GREY_EXTRA_LIGHT)
                    .add_text_with_font(title, fonts::FONT_SATOSHI_MEDIUM_26)
                    .add_newline()
                    .add_offset(Offset::y(24))
                    .add_color(theme::GREY_LIGHT)
                    .add_line_spacing(16)
                    .add_text_with_font(description, fonts::FONT_MONO_MEDIUM_38);
            }

            Some((op_layout, n_pages))
        } else {
            None
        };

        let flow = flow::continue_recovery_homepage::new_continue_recovery_homepage(
            text,
            subtext,
            recovery_type,
            show_instructions,
            shares_layout,
        )?;
        LayoutObj::new_root(flow)
    }

    fn flow_confirm_output(
        title: Option<TString<'static>>,
        subtitle: Option<TString<'static>>,
        description: Option<TString<'static>>,
        extra: Option<TString<'static>>,
        message: TString<'static>,
        amount: Option<TString<'static>>,
        chunkify: bool,
        text_mono: bool,
        account_title: TString<'static>,
        account: Option<TString<'static>>,
        account_path: Option<TString<'static>>,
        br_code: u16,
        br_name: TString<'static>,
        address_item: Option<Obj>,
        extra_item: Option<Obj>,
        summary_items: Option<Obj>,
        fee_items: Option<Obj>,
        summary_title: Option<TString<'static>>,
        summary_br_code: Option<u16>,
        summary_br_name: Option<TString<'static>>,
        cancel_text: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut main_paragraphs = ParagraphVecShort::new();
        if let Some(description) = description {
            main_paragraphs.add(
                Paragraph::new(&theme::TEXT_REGULAR, description)
                    .with_bottom_padding(theme::PROPS_SPACING),
            );
        }
        if let Some(extra) = extra {
            main_paragraphs.add(
                Paragraph::new(&theme::TEXT_SMALL, extra).with_bottom_padding(theme::PROPS_SPACING),
            );
        }
        let font = if chunkify {
            &theme::TEXT_MONO_ADDRESS_CHUNKS
        } else if text_mono {
            &theme::TEXT_MONO_LIGHT_ELLIPSIS
        } else {
            &theme::TEXT_REGULAR
        };
        main_paragraphs.add(Paragraph::new(font, message));

        let (address_title, address_paragraph) = if let Some(address_item) = address_item {
            let [key, value, _is_data]: [Obj; 3] = util::iter_into_array(address_item)?;
            let paragraph = Paragraph::new(
                &theme::TEXT_MONO_ADDRESS_CHUNKS,
                value.try_into().unwrap_or(TString::empty()),
            );
            (
                Some(key.try_into().unwrap_or(TString::empty())),
                Some(paragraph),
            )
        } else {
            (None, None)
        };

        // collect available info
        let account_paragraphs = {
            let mut paragraphs = ParagraphVecShort::new();
            if let Some(account) = account {
                let mut para = Paragraph::new(&theme::TEXT_MONO_LIGHT, account);
                if account_path.is_some() {
                    para = para.with_bottom_padding(theme::PROPS_SPACING);
                }
                paragraphs
                    .add(
                        Paragraph::new(&theme::TEXT_SMALL_LIGHT, TR::words__wallet)
                            .with_bottom_padding(theme::PROP_INNER_SPACING)
                            .no_break(),
                    )
                    .add(para);
            }
            if let Some(path) = account_path {
                paragraphs
                    .add(
                        Paragraph::new(
                            &theme::TEXT_SMALL_LIGHT,
                            TString::from_translation(TR::address_details__derivation_path),
                        )
                        .with_bottom_padding(theme::PROP_INNER_SPACING)
                        .no_break(),
                    )
                    .add(Paragraph::new(&theme::TEXT_MONO_LIGHT, path));
            }
            if paragraphs.is_empty() {
                None
            } else {
                Some(paragraphs)
            }
        };

        let summary_paragraphs = if let Some(items) = summary_items {
            Some(PropsList::new_styled(
                items,
                &theme::TEXT_SMALL_LIGHT,
                &theme::TEXT_MONO_MEDIUM_LIGHT,
                &theme::TEXT_MONO_MEDIUM_LIGHT,
                theme::PROP_INNER_SPACING,
                theme::PROPS_SPACING,
            )?)
        } else {
            None
        };

        let fee_paragraphs = if let Some(items) = fee_items {
            Some(PropsList::new_styled(
                items,
                &theme::TEXT_SMALL_LIGHT,
                &theme::TEXT_MONO_MEDIUM_LIGHT,
                &theme::TEXT_MONO_MEDIUM_LIGHT_DATA,
                theme::PROP_INNER_SPACING,
                theme::PROPS_SPACING,
            )?)
        } else {
            None
        };

        let (extra_title, extra_paragraph) = if let Some(extra_item) = extra_item {
            let [key, value, _is_data]: [Obj; 3] = util::iter_into_array(extra_item)?;
            let paragraph = Paragraph::new(
                &theme::TEXT_MONO_ADDRESS,
                value.try_into().unwrap_or(TString::empty()),
            );
            (
                Some(key.try_into().unwrap_or(TString::empty())),
                Some(paragraph),
            )
        } else {
            (None, None)
        };

        let flow = flow::confirm_output::new_confirm_output(
            title,
            subtitle,
            main_paragraphs,
            amount,
            br_name,
            br_code,
            account_title,
            account_paragraphs,
            address_title,
            address_paragraph,
            summary_title,
            summary_paragraphs,
            summary_br_code,
            summary_br_name,
            extra_title,
            extra_paragraph,
            fee_paragraphs,
            cancel_text,
        )?;
        Ok(flow)
    }

    fn flow_confirm_set_new_code(is_wipe_code: bool) -> Result<impl LayoutMaybeTrace, Error> {
        let flow = flow::confirm_set_new_code::new_set_new_code(is_wipe_code)?;
        Ok(flow)
    }

    fn flow_get_address(
        address: TString<'static>,
        title: TString<'static>,
        subtitle: Option<TString<'static>>,
        description: Option<TString<'static>>,
        hint: Option<TString<'static>>,
        chunkify: bool,
        address_qr: TString<'static>,
        case_sensitive: bool,
        account: Option<TString<'static>>,
        path: Option<TString<'static>>,
        xpubs: Obj,
        br_code: u16,
        br_name: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let flow = flow::receive::new_receive(
            title,
            subtitle,
            description,
            hint,
            ContentType::Address(address),
            chunkify,
            address_qr,
            case_sensitive,
            account,
            path,
            xpubs,
            br_code,
            br_name,
        )?;
        Ok(flow)
    }

    fn flow_get_pubkey(
        pubkey: TString<'static>,
        title: TString<'static>,
        subtitle: Option<TString<'static>>,
        hint: Option<TString<'static>>,
        pubkey_qr: TString<'static>,
        account: Option<TString<'static>>,
        path: Option<TString<'static>>,
        br_code: u16,
        br_name: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let flow = flow::receive::new_receive(
            title,
            subtitle,
            None,
            hint,
            ContentType::PublicKey(pubkey),
            false,
            pubkey_qr,
            true,
            account,
            path,
            Obj::const_none(),
            br_code,
            br_name,
        )?;
        Ok(flow)
    }

    fn multiple_pages_texts(
        _title: TString<'static>,
        _verb: TString<'static>,
        _items: Gc<List>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn prompt_backup() -> Result<impl LayoutMaybeTrace, Error> {
        let flow = flow::prompt_backup::new_prompt_backup()?;
        Ok(flow)
    }

    fn request_bip39(
        prompt: TString<'static>,
        prefill_word: TString<'static>,
        can_go_back: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(MnemonicKeyboard::new(
            prefill_word.map(Bip39Input::prefilled_word),
            prompt,
            can_go_back,
        ));
        Ok(layout)
    }

    fn request_slip39(
        prompt: TString<'static>,
        prefill_word: TString<'static>,
        can_go_back: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(MnemonicKeyboard::new(
            prefill_word.map(Slip39Input::prefilled_word),
            prompt,
            can_go_back,
        ));

        Ok(layout)
    }

    fn request_number(
        title: TString<'static>,
        count: u32,
        min_count: u32,
        max_count: u32,
        description: Option<TString<'static>>,
        more_info_callback: Option<impl Fn(u32) -> TString<'static> + 'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let description = description.unwrap_or(TString::empty());
        let flow = flow::request_number::new_request_number(
            title,
            count,
            min_count,
            max_count,
            description,
            unwrap!(more_info_callback),
        )?;
        Ok(flow)
    }

    fn request_duration(
        title: TString<'static>,
        duration_ms: u32,
        min_ms: u32,
        max_ms: u32,
        description: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let description = description.unwrap_or(TString::empty());
        let component = ValueInputScreen::new(
            DurationInput::new(
                Duration::from_millis(min_ms),
                Duration::from_millis(max_ms),
                Duration::from_millis(duration_ms),
            ),
            description,
        )
        .with_header(Header::new(title));

        let layout = RootComponent::new(component);

        Ok(layout)
    }

    fn request_pin(
        prompt: TString<'static>,
        attempts: TString<'static>,
        allow_cancel: bool,
        wrong_pin: bool,
        last_attempt: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let warning = if wrong_pin {
            Some(TR::pin__wrong_pin.into())
        } else {
            None
        };

        let layout = RootComponent::new(PinKeyboard::new(
            prompt,
            attempts,
            warning,
            allow_cancel,
            last_attempt,
        ));
        Ok(layout)
    }

    fn request_passphrase(
        prompt: TString<'static>,
        prompt_empty: TString<'static>,
        max_len: usize,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let flow = flow::request_passphrase::new_request_passphrase(prompt, prompt_empty, max_len)?;
        Ok(flow)
    }

    fn request_string(
        prompt: TString<'static>,
        max_len: usize,
        allow_empty: bool,
        prefill: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let input = LabelInput::new(max_len, prefill, true, allow_empty);
        let layout = RootComponent::new(StringKeyboard::new(prompt, input));
        Ok(layout)
    }

    fn select_menu(
        items: heapless::Vec<TString<'static>, MAX_MENU_ITEMS>,
        _current: usize,
        cancel: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut menu = VerticalMenu::<ShortMenuVec>::empty();
        for text in &items {
            menu.item(Button::new_menu_item(*text, theme::menu_item_title()));
        }
        if let Some(text) = cancel {
            menu.item(Button::new_cancel_menu_item(text));
        }
        let screen = VerticalMenuScreen::new(menu)
            .with_header(Header::new(TString::empty()).with_close_button())
            .map(move |msg| {
                let choice = match msg {
                    VerticalMenuScreenMsg::Selected(i) => i,
                    VerticalMenuScreenMsg::Close => return Some(FlowMsg::Confirmed),
                    _ => return None,
                };
                Some(if cancel.is_some() && choice == items.len() {
                    FlowMsg::Cancelled
                } else {
                    FlowMsg::Choice(choice)
                })
            });

        flow::util::single_page(screen)
    }

    fn select_word(
        title: TString<'static>,
        description: TString<'static>,
        words: [TString<'static>; MAX_WORD_QUIZ_ITEMS],
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let component = SelectWordScreen::new(words, description).with_header(Header::new(title));

        let layout = RootComponent::new(component);

        Ok(layout)
    }

    fn select_word_count(recovery_type: RecoveryType) -> Result<impl LayoutMaybeTrace, Error> {
        let description = TR::recovery__num_of_words.into();
        let title = match recovery_type {
            RecoveryType::DryRun => TR::reset__check_wallet_backup_title,
            RecoveryType::Normal | RecoveryType::UnlockRepeatedBackup => {
                TR::recovery__title_recover
            }
        };
        let content = if matches!(recovery_type, RecoveryType::UnlockRepeatedBackup) {
            SelectWordCountScreen::new_multi_share(description)
        } else {
            SelectWordCountScreen::new_single_share(description)
        }
        .with_header(Header::new(title.into()));
        let layout = RootComponent::new(content);
        Ok(layout)
    }

    fn set_brightness(current_brightness: Option<u8>) -> Result<impl LayoutMaybeTrace, Error> {
        let init_value = match current_brightness {
            Some(value) => {
                // Set the brightness immediately so it is applied in the `_first_paint` UI
                // layout function
                unwrap!(storage::set_brightness(value));
                value
            }
            None => theme::backlight::get_backlight_normal(),
        };
        let min = theme::backlight::get_backlight_min();
        let max = theme::backlight::get_backlight_max();

        let screen = SetBrightnessScreen::new(min, max, init_value);
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn show_address_details(
        _qr_title: TString<'static>,
        _address: TString<'static>,
        _case_sensitive: bool,
        _details_title: TString<'static>,
        _account: Option<TString<'static>>,
        _path: Option<TString<'static>>,
        _xpubs: Obj,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn show_checklist(
        title: TString<'static>,
        button: TString<'static>,
        active: usize,
        items: [TString<'static>; MAX_CHECKLIST_ITEMS],
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut paragraphs = ParagraphVecShort::new();
        for (i, item) in items.into_iter().enumerate() {
            let style = match i.cmp(&active) {
                Ordering::Less => &theme::TEXT_CHECKLIST_INACTIVE,
                Ordering::Equal => &theme::TEXT_MEDIUM,
                Ordering::Greater => &theme::TEXT_CHECKLIST_INACTIVE,
            };
            paragraphs.add(Paragraph::new(style, item));
        }

        let checklist_content = Checklist::from_paragraphs(
            theme::ICON_CHEVRON_RIGHT_MINI,
            theme::ICON_CHECKMARK_MINI,
            active,
            paragraphs
                .into_paragraphs()
                .with_placement(LinearPlacement::vertical().with_spacing(theme::CHECKLIST_SPACING)),
        )
        .with_check_width(theme::CHECKLIST_CHECK_WIDTH)
        .with_icon_done_color(theme::GREEN_LIGHT)
        .with_done_offset(theme::CHECKLIST_DONE_OFFSET)
        .with_current_offset(theme::CHECKLIST_CURRENT_OFFSET);

        let layout = RootComponent::new(
            TextScreen::new(checklist_content)
                .with_header(Header::new(title))
                .with_action_bar(ActionBar::new_double(
                    Button::with_icon(theme::ICON_CROSS),
                    Button::with_text(button),
                )),
        );

        Ok(layout)
    }

    fn show_danger(
        title: TString<'static>,
        description: TString<'static>,
        value: TString<'static>,
        menu_title: Option<TString<'static>>,
        verb_cancel: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let flow =
            flow::show_danger::new_show_danger(title, description, value, menu_title, verb_cancel)?;
        Ok(flow)
    }

    fn show_error(
        title: TString<'static>,
        button: TString<'static>,
        description: TString<'static>,
        allow_cancel: bool,
        _time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        let content = Paragraphs::new(Paragraph::new(&theme::firmware::TEXT_REGULAR, description))
            .with_placement(LinearPlacement::vertical());

        let action_bar = if allow_cancel {
            ActionBar::new_double(
                Button::with_icon(theme::ICON_CLOSE),
                Button::with_text(button),
            )
        } else {
            ActionBar::new_single(Button::with_text(button))
        };
        let screen = TextScreen::new(content)
            .with_header(
                Header::new(title)
                    .with_icon(theme::ICON_WARNING, theme::ORANGE)
                    .with_text_style(theme::label_title_danger()),
            )
            .with_action_bar(action_bar);
        let obj = LayoutObj::new(screen)?;
        Ok(obj)
    }

    fn show_group_share_success(
        lines: [TString<'static>; MAX_GROUP_SHARE_LINES],
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = Paragraph::new(&theme::TEXT_REGULAR, lines[0])
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical());

        let layout = RootComponent::new(
            TextScreen::new(paragraphs)
                .with_header(
                    Header::new(TR::words__title_done.into())
                        .with_icon(theme::ICON_DONE, theme::GREEN_LIGHT)
                        .with_text_style(theme::label_title_confirm()),
                )
                .with_action_bar(ActionBar::new_single(Button::with_text(
                    TR::buttons__continue.into(),
                ))),
        );
        Ok(layout)
    }

    fn show_homescreen(
        label: TString<'static>,
        notification: Option<TString<'static>>,
        notification_level: u8,
        lockable: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let locked = false;
        let bootscreen = false;
        let coinjoin_authorized = false;
        let notification = notification.map(|w| (w, notification_level));
        let layout = RootComponent::new(Homescreen::new(
            label,
            lockable,
            locked,
            bootscreen,
            coinjoin_authorized,
            notification,
        )?);
        Ok(layout)
    }

    fn show_device_menu(
        init_submenu_idx: Option<u8>,
        backup_failed: bool,
        backup_needed: bool,
        ble_enabled: bool,
        paired_devices: heapless::Vec<
            (TString<'static>, Option<[TString<'static>; 2]>),
            MAX_PAIRED_DEVICES,
        >,
        connected_idx: Option<u8>,
        pin_enabled: Option<bool>,
        auto_lock: Option<[TString<'static>; 2]>,
        wipe_code_enabled: Option<bool>,
        backup_check_allowed: bool,
        device_name: Option<TString<'static>>,
        brightness: Option<TString<'static>>,
        haptics_enabled: Option<bool>,
        led_enabled: Option<bool>,
        about_items: Obj,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(DeviceMenuScreen::new(
            init_submenu_idx,
            backup_failed,
            backup_needed,
            ble_enabled,
            paired_devices,
            connected_idx,
            pin_enabled,
            auto_lock,
            wipe_code_enabled,
            backup_check_allowed,
            device_name,
            brightness,
            haptics_enabled,
            led_enabled,
            about_items,
        )?);
        Ok(layout)
    }

    fn show_pairing_device_name(
        description: StrBuffer,
        device_name: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let text_style = theme::firmware::TEXT_REGULAR;
        let font = text_style.text_font;
        let mut ops = OpTextLayout::new(text_style);
        for part in interpolate::parse(description) {
            match part {
                interpolate::Item::Text(s) => {
                    ops.add_color(text_style.text_color);
                    ops.add_text_with_font(s, font);
                }
                interpolate::Item::Arg(0) => {
                    ops.add_color(theme::GREEN);
                    ops.add_text_with_font(device_name, font);
                }
                _ => return Err(Error::OutOfRange),
            };
        }
        let screen = TextScreen::new(FormattedText::new(ops))
            .with_header(Header::new(TR::thp__pair_new_device.into()).with_close_button())
            .with_action_bar(ActionBar::new_text_only(
                TR::instructions__continue_in_app.into(),
            ));
        #[cfg(feature = "ble")]
        let screen = BLEHandler::new(screen, BLEHandlerMode::WaitingForPairingRequest);
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    #[cfg(feature = "ble")]
    fn show_ble_pairing_code(
        title: TString<'static>,
        description: TString<'static>,
        code: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut ops = OpTextLayout::new(theme::firmware::TEXT_REGULAR);
        ops.add_text_with_font(description, fonts::FONT_SATOSHI_REGULAR_38)
            .add_newline()
            .add_newline()
            .add_newline()
            .add_alignment(Alignment::Center)
            .add_text_with_font(code, fonts::FONT_SATOSHI_EXTRALIGHT_72);
        let screen = BLEHandler::new(
            TextScreen::new(FormattedText::new(ops))
                .with_header(Header::new(title))
                .with_action_bar(ActionBar::new_cancel_confirm()),
            BLEHandlerMode::WaitingForPairingCancel,
        );
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    #[cfg(feature = "ble")]
    fn wait_ble_host_confirmation() -> Result<impl LayoutMaybeTrace, Error> {
        let screen = BLEHandler::new(
            TextScreen::new(
                Paragraph::new(&theme::TEXT_REGULAR, TR::ble__waiting_for_host)
                    .into_paragraphs()
                    .with_placement(LinearPlacement::vertical()),
            )
            .with_header(Header::new(TR::ble__pairing_title.into()).with_close_button()),
            BLEHandlerMode::WaitingForPairingCompletion,
        );
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn show_thp_pairing_code(
        title: TString<'static>,
        description: TString<'static>,
        code: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let flow =
            flow::show_thp_pairing_code::new_show_thp_pairing_code(title, description, code)?;
        Ok(flow)
    }

    fn confirm_thp_pairing(
        title: TString<'static>,
        description: (StrBuffer, Obj),
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let (format, args_obj) = description;
        let args: heapless::Vec<TString<'static>, 2> = util::iter_into_vec(args_obj)?;
        let style = theme::firmware::TEXT_REGULAR;
        let mut ops = OpTextLayout::new(style);
        for part in interpolate::parse(format) {
            match part {
                interpolate::Item::Text(s) => {
                    ops.add_text_with_font(s, style.text_font);
                }
                interpolate::Item::Arg(i) => match args.get(i) {
                    Some(&s) => {
                        ops.add_color(theme::YELLOW);
                        ops.add_text_with_font(s, style.text_font);
                        ops.add_color(style.text_color);
                    }
                    None => return Err(Error::OutOfRange),
                },
            };
        }
        let screen = TextScreen::new(FormattedText::new(ops))
            .with_header(Header::new(title))
            .with_action_bar(ActionBar::new_cancel_confirm());
        Ok(RootComponent::new(screen))
    }

    fn show_info(
        title: TString<'static>,
        description: TString<'static>,
        button: TString<'static>,
        _time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        let content = Paragraphs::new(Paragraph::new(&theme::TEXT_REGULAR, description))
            .with_placement(LinearPlacement::vertical());

        let screen = TextScreen::new(content)
            .with_header(Header::new(title))
            .with_action_bar(ActionBar::new_single(Button::with_text(button)));
        let obj = LayoutObj::new(screen)?;
        Ok(obj)
    }

    fn show_info_with_cancel(
        title: TString<'static>,
        items: Obj,
        _horizontal: bool,
        chunkify: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let value_mono_font = if chunkify {
            &theme::TEXT_MONO_ADDRESS_CHUNKS
        } else {
            &theme::TEXT_MONO_LIGHT
        };

        let paragraphs = PropsList::new_styled(
            items,
            &theme::TEXT_SMALL_LIGHT,
            &theme::TEXT_MONO_MEDIUM_LIGHT,
            value_mono_font,
            theme::PROP_INNER_SPACING,
            theme::PROPS_SPACING,
        )?
        .into_paragraphs()
        .with_placement(LinearPlacement::vertical());

        let screen =
            TextScreen::new(paragraphs).with_header(Header::new(title).with_close_button());
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn show_lockscreen(
        label: TString<'static>,
        bootscreen: bool,
        coinjoin_authorized: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let locked = true;
        let notification = None;
        let hold = false;
        let layout = RootComponent::new(Homescreen::new(
            label,
            hold,
            locked,
            bootscreen,
            coinjoin_authorized,
            notification,
        )?);
        Ok(layout)
    }

    fn show_mismatch(title: TString<'static>) -> Result<impl LayoutMaybeTrace, Error> {
        let description: TString = TR::addr_mismatch__contact_support_at.into();
        let url: TString = TR::addr_mismatch__support_url.into();
        let button: TString = TR::buttons__quit.into();

        let text_style = theme::TEXT_REGULAR;
        let mut ops = OpTextLayout::new(text_style);
        ops.add_text_with_font(description, text_style.text_font)
            .add_text_with_font(url, theme::TEXT_MONO_MEDIUM.text_font);

        let screen = TextScreen::new(FormattedText::new(ops))
            .with_header(Header::new(title))
            .with_action_bar(ActionBar::new_double(
                Button::with_icon(theme::ICON_CROSS),
                Button::with_text(button),
            ));

        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn show_progress(
        description: TString<'static>,
        indeterminate: bool,
        title: Option<TString<'static>>,
        danger: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let (title, description) = if let Some(title) = title {
            (title, description)
        } else {
            (description, "".into())
        };

        let layout = RootComponent::new(ProgressScreen::new_progress(
            title,
            indeterminate,
            description,
            danger,
        ));
        Ok(layout)
    }

    fn show_progress_coinjoin(
        description: TString<'static>,
        indeterminate: bool,
        time_ms: u32,
        skip_first_paint: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        let progress = ProgressScreen::new_coinjoin_progress(
            TR::coinjoin__title_progress.into(),
            indeterminate,
            description,
        );
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
        value: Obj,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let mut vec = ParagraphVecShort::new();
        if Obj::is_str(value) {
            let text: TString = value.try_into()?;
            unwrap!(vec.push(Paragraph::new(&theme::TEXT_MONO_ADDRESS_CHUNKS, text)));
        } else {
            for property in IterBuf::new().try_iterate(value)? {
                let [header, text, _is_data]: [Obj; 3] = util::iter_into_array(property)?;
                let header = header
                    .try_into_option::<TString>()?
                    .unwrap_or_else(TString::empty);
                let text = text
                    .try_into_option::<TString>()?
                    .unwrap_or_else(TString::empty);

                unwrap!(vec.push(Paragraph::new(&theme::TEXT_SMALL, header)));
                let mut value_paragraph = Paragraph::new(
                    if header.is_empty() {
                        &theme::TEXT_MONO_ADDRESS_CHUNKS
                    } else {
                        &theme::TEXT_MONO_LIGHT
                    },
                    text,
                );
                if header.is_empty() {
                    value_paragraph = value_paragraph.with_bottom_padding(20);
                }
                unwrap!(vec.push(value_paragraph));
            }
        };

        let screen = TextScreen::new(
            vec.into_paragraphs()
                .with_placement(LinearPlacement::vertical()),
        )
        .with_header(Header::new(title).with_close_button());

        let obj = RootComponent::new(screen);
        Ok(obj)
    }

    fn show_share_words(
        _words: heapless::Vec<TString<'static>, 33>,
        _title: Option<TString<'static>>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn show_share_words_extended(
        words: heapless::Vec<TString<'static>, 33>,
        subtitle: Option<TString<'static>>,
        instructions: Obj,
        instructions_verb: Option<TString<'static>>,
        // Irrelevant for Eckhart because the footer is dynamic
        _text_footer: Option<TString<'static>>,
        text_confirm: TString<'static>,
        text_check: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let instructions_paragraphs = {
            let mut vec = ParagraphVecShort::new();
            for item in IterBuf::new().try_iterate(instructions)? {
                let text: TString = item.try_into()?;
                vec.add(Paragraph::new(&theme::TEXT_REGULAR, text));
            }
            match vec.is_empty() {
                true => None,
                false => Some(vec),
            }
        };

        let flow = flow::show_share_words::new_show_share_words_flow(
            words,
            subtitle.unwrap_or(TString::empty()),
            instructions_paragraphs,
            instructions_verb,
            text_confirm,
            text_check,
        )?;
        Ok(flow)
    }

    fn show_remaining_shares(_pages_iterable: Obj) -> Result<impl LayoutMaybeTrace, Error> {
        Err::<RootComponent<Empty, ModelUI>, Error>(Error::NotImplementedError)
    }

    fn show_simple(
        text: TString<'static>,
        title: Option<TString<'static>>,
        button: Option<TString<'static>>,
    ) -> Result<Gc<LayoutObj>, Error> {
        let paragraphs = Paragraph::new(&theme::TEXT_REGULAR, text)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical());

        let mut screen = TextScreen::new(paragraphs);
        if let Some(title) = title {
            screen = screen.with_header(Header::new(title));
        }
        if let Some(button) = button {
            screen = screen.with_action_bar(ActionBar::new_single(Button::with_text(button)));
        }

        let obj = LayoutObj::new(screen)?;
        Ok(obj)
    }

    fn show_success(
        title: TString<'static>,
        button: TString<'static>,
        description: TString<'static>,
        allow_cancel: bool,
        time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        let paragraphs = Paragraph::new(&theme::TEXT_REGULAR, description)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical());
        let header = Header::new(title)
            .with_icon(theme::ICON_DONE, theme::GREEN_LIGHT)
            .with_text_style(theme::label_title_confirm());
        let action_bar = if allow_cancel {
            ActionBar::new_double(
                Button::with_icon(theme::ICON_CROSS),
                Button::with_text(button),
            )
        } else if time_ms > 0 {
            ActionBar::new_timeout(Button::with_text(button), Duration::from_millis(time_ms))
        } else {
            ActionBar::new_single(Button::with_text(button))
        };
        let screen = TextScreen::new(paragraphs)
            .with_header(header)
            .with_action_bar(action_bar);
        let layout = LayoutObj::new(screen)?;
        Ok(layout)
    }

    fn show_wait_text(text: TString<'static>) -> Result<impl LayoutMaybeTrace, Error> {
        let paragraphs = Paragraph::new(&theme::TEXT_REGULAR, text)
            .into_paragraphs()
            .with_placement(LinearPlacement::vertical());
        let screen = TextScreen::new(paragraphs);
        let layout = RootComponent::new(screen);
        Ok(layout)
    }

    fn show_warning(
        title: TString<'static>,
        button: TString<'static>,
        value: TString<'static>,
        description: TString<'static>,
        allow_cancel: bool,
        danger: bool,
    ) -> Result<Gc<LayoutObj>, Error> {
        let paragraphs = Paragraphs::new([
            Paragraph::new(&theme::TEXT_REGULAR, description),
            Paragraph::new(&theme::TEXT_REGULAR, value),
        ])
        .with_placement(LinearPlacement::vertical())
        .with_spacing(theme::TEXT_VERTICAL_SPACING);

        let (color, style) = if danger {
            (theme::ORANGE, theme::label_title_danger())
        } else {
            (theme::YELLOW, theme::label_title_warning())
        };

        let header = Header::new(title)
            .with_icon(theme::ICON_INFO, color)
            .with_text_style(style);
        let action_bar = if allow_cancel {
            ActionBar::new_double(
                Button::with_icon(theme::ICON_CROSS),
                Button::with_text(button),
            )
        } else {
            ActionBar::new_single(Button::with_text(button))
        };
        let screen = TextScreen::new(paragraphs)
            .with_header(header)
            .with_action_bar(action_bar);
        let layout = LayoutObj::new(screen)?;
        Ok(layout)
    }

    fn tutorial() -> Result<impl LayoutMaybeTrace, Error> {
        let flow = flow::show_tutorial::new_show_tutorial()?;
        Ok(flow)
    }

    fn process_ipc_message(data: &[u8]) -> Result<Gc<LayoutObj>, Error> {
        // Deserialize the rkyv archived data directly from the static buffer
        let archived = unsafe { rkyv::access_unchecked::<ArchivedTrezorUiEnum>(data) };

        // Access the archived data zero-copy using StrBuffer::from_ptr_and_len
        match archived {
            ArchivedTrezorUiEnum::ConfirmAction { title, content } => {
                // Create StrBuffers pointing directly to the archived data
                // This is safe because the data has 'static lifetime
                let title_buf =
                    unsafe { StrBuffer::from_ptr_and_len(title.data.as_ptr(), title.len as usize) };
                let content_buf = unsafe {
                    StrBuffer::from_ptr_and_len(content.data.as_ptr(), content.len as usize)
                };

                // Convert StrBuffers to TString for the API
                let layout = Self::confirm_action(
                    title_buf.into(),
                    Some(content_buf.into()),
                    None,  // description
                    None,  // subtitle
                    None,  // verb
                    None,  // verb_cancel
                    false, // hold
                    false, // hold_danger
                    false, // reverse
                    false, // prompt_screen
                    None,  // prompt_title
                    false, // external_menu
                )?;
                LayoutObj::new_root(layout)
            }
            ArchivedTrezorUiEnum::ConfirmProperties { title, props } => {
                // Create StrBuffers pointing directly to the archived data
                // This is safe because the data has 'static lifetime
                let title_buf =
                    unsafe { StrBuffer::from_ptr_and_len(title.data.as_ptr(), title.len as usize) };

                // Build array of tuples for properties list
                let mut tuple_objs = heapless::Vec::<Obj, 5>::new();
                for i in 0..(props.len as usize) {
                    let str1 = unsafe {
                        core::str::from_raw_parts(
                            props.data[i].0.data.as_ptr(),
                            props.data[i].0.len as usize,
                        )
                    };
                    let str2 = unsafe {
                        core::str::from_raw_parts(
                            props.data[i].1.data.as_ptr(),
                            props.data[i].1.len as usize,
                        )
                    };
                    let prop: Obj = unwrap!((
                        unwrap!(Obj::try_from(str1)),
                        unwrap!(Obj::try_from(str2)),
                        Obj::from(false),
                    )
                        .try_into());

                    unwrap!(tuple_objs.push(prop));
                }

                // Create List from tuples
                let items = List::alloc(&tuple_objs)?;

                // Convert StrBuffers to TString for the API
                let layout = Self::confirm_properties(
                    title_buf.into(),
                    None,
                    items.into(),
                    true,
                    None,
                    false,
                )?;
                LayoutObj::new_root(layout)
            }
            ArchivedTrezorUiEnum::Warning { title, content } => {
                // Create StrBuffers pointing directly to the archived data
                // This is safe because the data has 'static lifetime
                let title_buf =
                    unsafe { StrBuffer::from_ptr_and_len(title.data.as_ptr(), title.len as usize) };
                let content_buf = unsafe {
                    StrBuffer::from_ptr_and_len(content.data.as_ptr(), content.len as usize)
                };

                // Convert StrBuffers to TString for the API
                Self::show_warning(
                    title_buf.into(),
                    TR::buttons__continue.into(),
                    content_buf.into(),
                    TString::empty(),
                    false,
                    false,
                )
            }
            ArchivedTrezorUiEnum::Success { title, content } => {
                // Create StrBuffers pointing directly to the archived data
                // This is safe because the data has 'static lifetime
                let title_buf =
                    unsafe { StrBuffer::from_ptr_and_len(title.data.as_ptr(), title.len as usize) };
                let content_buf = unsafe {
                    StrBuffer::from_ptr_and_len(content.data.as_ptr(), content.len as usize)
                };

                // Convert StrBuffers to TString for the API
                Self::show_success(
                    title_buf.into(),
                    TR::buttons__continue.into(),
                    content_buf.into(),
                    false,
                    0,
                )
            }
            ArchivedTrezorUiEnum::RequestString { prompt } => {
                // Create StrBuffers pointing directly to the archived data
                // This is safe because the data has 'static lifetime
                let prompt_buf = unsafe {
                    StrBuffer::from_ptr_and_len(prompt.data.as_ptr(), prompt.len as usize)
                };

                // Convert StrBuffers to TString for the API
                let layout = Self::request_string(
                    prompt_buf.into(),
                    50, // max_len
                    false,
                    None,
                )?;

                LayoutObj::new_root(layout)
            }
            ArchivedTrezorUiEnum::RequestNumber {
                title,
                content,
                initial,
                min,
                max,
            } => {
                // Create StrBuffers pointing directly to the archived data
                // This is safe because the data has 'static lifetime
                let title_buf =
                    unsafe { StrBuffer::from_ptr_and_len(title.data.as_ptr(), title.len as usize) };
                let content_buf = unsafe {
                    StrBuffer::from_ptr_and_len(content.data.as_ptr(), content.len as usize)
                };

                // Convert StrBuffers to TString for the API
                // Dereference archived u32 values to get normal u32
                let layout = Self::request_number(
                    title_buf.into(),
                    (*initial).into(),
                    (*min).into(),
                    (*max).into(),
                    Some(content_buf.into()),
                    Some(|_| TString::empty()),
                )?;

                LayoutObj::new_root(layout)
            }
        }
    }
}
