//! Constructors of the [`super`] structs, taking plain Rust types.

use stabby::option::Option as StabbyOption;
use stabby::slice::Slice;
use stabby::str::Str;

use super::{
    ConfirmAction, ConfirmProperties, ConfirmSummary, ConfirmTrade, ConfirmValue,
    ConfirmValueIntro, ConfirmWithInfo, Property, RequestNumber, SelectMenu, ShowAddress,
    ShowDanger, ShowInfoWithCancel, ShowMismatch, ShowProperties, ShowPublicKey, ShowSuccess,
    ShowWarning, StrExt,
};

/// Converts an optional `&str` constructor argument into the
/// niche-friendly `StabbyOption<Slice<u8>>` field representation.
pub(crate) fn opt_bytes(s: Option<&str>) -> StabbyOption<Slice<'_, u8>> {
    s.map(|s| Slice::from(s.as_bytes())).into()
}

/// Recovers the `&str` an `opt_bytes`-produced field holds, if any.
///
/// # Safety
///
/// `bytes`, if present, must have come from `opt_bytes` applied to a
/// genuine `&str` (true for every field on every type in [`super`]).
pub fn as_opt_str(bytes: StabbyOption<Slice<'_, u8>>) -> Option<&str> {
    core::option::Option::from(bytes).map(|b: Slice<'_, u8>| {
        // SAFETY: see function doc.
        unsafe { core::str::from_utf8_unchecked(b.as_slice()) }
    })
}

impl<'a> Property<'a> {
    pub fn new(key: &'a str, value: &'a str, mono: bool) -> Self {
        Self {
            key: key.into(),
            value: value.into(),
            mono,
        }
    }

    pub fn mono(key: &'a str, value: &'a str) -> Self {
        Self::new(key, value, true)
    }

    pub fn plain(key: &'a str, value: &'a str) -> Self {
        Self::new(key, value, false)
    }
}

impl<'a> StrExt<'a> {
    pub fn new(key: &'a str, mono: bool) -> Self {
        Self {
            key: key.into(),
            mono,
        }
    }

    pub fn mono(key: &'a str) -> Self {
        Self::new(key, true)
    }

    pub fn plain(key: &'a str) -> Self {
        Self::new(key, false)
    }
}

impl<'a> SelectMenu<'a> {
    pub fn new(items: &'a [Str<'a>], cancel: Option<&'a str>, br_code: i32) -> Self {
        Self {
            items: items.into(),
            cancel: opt_bytes(cancel),
            br_code,
        }
    }
}

impl<'a> ConfirmTrade<'a> {
    pub fn new(
        title: &'a str,
        subtitle: &'a str,
        buy: &'a str,
        sell: Option<&'a str>,
        back_button: bool,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            title: title.into(),
            subtitle: subtitle.into(),
            buy: buy.into(),
            sell: opt_bytes(sell),
            back_button,
            br_name: opt_bytes(br_name),
            br_code,
        }
    }
}

impl<'a> ConfirmAction<'a> {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        title: &'a str,
        action: &'a str,
        description: Option<&'a str>,
        subtitle: Option<&'a str>,
        hold: bool,
        verb: Option<&'a str>,
        cancel: bool,
        br_name: Option<&'a str>,
        br_code: i32,
        external_menu: bool,
    ) -> Self {
        Self {
            title: title.into(),
            action: action.into(),
            description: opt_bytes(description),
            subtitle: opt_bytes(subtitle),
            hold,
            cancel,
            verb: opt_bytes(verb),
            br_name: opt_bytes(br_name),
            br_code,
            external_menu,
        }
    }
}

impl<'a> ConfirmSummary<'a> {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        title: &'a str,
        amount: Option<&'a str>,
        amount_label: Option<&'a str>,
        fee: &'a str,
        fee_label: &'a str,
        account_title: Option<&'a str>,
        account_items: Option<&'a [Property<'a>]>,
        extra_title: Option<&'a str>,
        extra_items: Option<&'a [Property<'a>]>,
        back_button: bool,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            title: title.into(),
            amount: opt_bytes(amount),
            amount_label: opt_bytes(amount_label),
            fee: fee.into(),
            fee_label: fee_label.into(),
            account_title: opt_bytes(account_title),
            account_items: account_items.map(Into::into).into(),
            extra_title: opt_bytes(extra_title),
            extra_items: extra_items.map(Into::into).into(),
            back_button,
            br_name: opt_bytes(br_name),
            br_code,
        }
    }
}

impl<'a> ConfirmValue<'a> {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        title: &'a str,
        content: &'a str,
        description: Option<&'a str>,
        br_name: Option<&'a str>,
        br_code: i32,
        is_data: bool,
        verb: Option<&'a str>,
        subtitle: Option<&'a str>,
        info: bool,
        hold: bool,
        chunkify: bool,
        page_counter: bool,
        cancel: bool,
        external_menu: bool,
        footer: Option<(&'a str, bool)>,
    ) -> Self {
        let (footer_text, footer_bold) = match footer {
            Some((text, bold)) => (opt_bytes(Some(text)), bold),
            None => (opt_bytes(None), false),
        };
        Self {
            title: title.into(),
            value: content.into(),
            description: opt_bytes(description),
            is_data,
            subtitle: opt_bytes(subtitle),
            verb: opt_bytes(verb),
            info,
            hold,
            chunkify,
            page_counter,
            cancel,
            br_name: opt_bytes(br_name),
            br_code,
            external_menu,
            footer_text,
            footer_bold,
        }
    }
}

impl<'a> ConfirmValueIntro<'a> {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        title: &'a str,
        value: &'a str,
        subtitle: Option<&'a str>,
        verb: Option<&'a str>,
        verb_cancel: Option<&'a str>,
        verb_view_all: Option<&'a str>,
        hold: bool,
        chunkify: bool,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            title: title.into(),
            value: value.into(),
            subtitle: opt_bytes(subtitle),
            verb: opt_bytes(verb),
            verb_cancel: opt_bytes(verb_cancel),
            verb_view_all: opt_bytes(verb_view_all),
            hold,
            chunkify,
            br_name: opt_bytes(br_name),
            br_code,
        }
    }
}

impl<'a> ShowWarning<'a> {
    pub fn new(
        title: &'a str,
        content: &'a str,
        verb: &'a str,
        br_name: Option<&'a str>,
        br_code: i32,
        allow_cancel: bool,
        danger: bool,
    ) -> Self {
        Self {
            title: title.into(),
            content: content.into(),
            verb: verb.into(),
            br_name: opt_bytes(br_name),
            br_code,
            allow_cancel,
            danger,
        }
    }
}

impl<'a> ShowMismatch<'a> {
    pub fn new(title: &'a str, br_code: i32) -> Self {
        Self {
            title: title.into(),
            br_code,
        }
    }
}

impl<'a> ShowDanger<'a> {
    pub fn new(
        title: &'a str,
        content: &'a str,
        br_name: Option<&'a str>,
        br_code: i32,
        verb_cancel: Option<&'a str>,
        menu_title: Option<&'a str>,
    ) -> Self {
        Self {
            title: title.into(),
            content: content.into(),
            br_name: opt_bytes(br_name),
            br_code,
            verb_cancel: opt_bytes(verb_cancel),
            menu_title: opt_bytes(menu_title),
        }
    }
}

impl<'a> ShowSuccess<'a> {
    pub fn new(
        title: &'a str,
        content: &'a str,
        button: &'a str,
        duration_ms: Option<u32>,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            title: title.into(),
            content: content.into(),
            button: button.into(),
            duration_ms: duration_ms.into(),
            br_name: opt_bytes(br_name),
            br_code,
        }
    }
}

impl<'a> RequestNumber<'a> {
    pub fn new(
        title: &'a str,
        content: &'a str,
        initial: u32,
        min: u32,
        max: u32,
        br_code: i32,
    ) -> Self {
        Self {
            title: title.into(),
            content: content.into(),
            initial,
            min,
            max,
            br_code,
        }
    }
}

impl<'a> ConfirmProperties<'a> {
    pub fn new(
        title: &'a str,
        props: &'a [Property<'a>],
        subtitle: Option<&'a str>,
        verb: Option<&'a str>,
        hold: bool,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            title: title.into(),
            props: props.into(),
            subtitle: opt_bytes(subtitle),
            verb: opt_bytes(verb),
            hold,
            br_name: opt_bytes(br_name),
            br_code,
        }
    }
}

impl<'a> ShowProperties<'a> {
    pub fn new(
        title: &'a str,
        props: &'a [Property<'a>],
        subtitle: Option<&'a str>,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            title: title.into(),
            props: props.into(),
            subtitle: opt_bytes(subtitle),
            br_name: opt_bytes(br_name),
            br_code,
        }
    }
}

impl<'a> ShowPublicKey<'a> {
    pub fn new(
        pubkey: &'a str,
        title: &'a str,
        account: Option<&'a str>,
        path: Option<&'a str>,
        warning: Option<&'a str>,
        br_name: &'a str,
        br_code: i32,
    ) -> Self {
        Self {
            pubkey: pubkey.into(),
            title: title.into(),
            account: opt_bytes(account),
            path: opt_bytes(path),
            warning: opt_bytes(warning),
            br_name: br_name.into(),
            br_code,
        }
    }
}

impl<'a> ShowInfoWithCancel<'a> {
    pub fn new(
        title: &'a str,
        items: &'a [Property<'a>],
        chunkify: bool,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            title: title.into(),
            items: items.into(),
            chunkify,
            br_name: opt_bytes(br_name),
            br_code,
        }
    }
}

impl<'a> ConfirmWithInfo<'a> {
    pub fn new(
        title: &'a str,
        subtitle: Option<&'a str>,
        items: &'a [StrExt<'a>],
        verb: &'a str,
        verb_info: Option<&'a str>,
        br_name: Option<&'a str>,
        br_code: i32,
    ) -> Self {
        Self {
            title: title.into(),
            subtitle: opt_bytes(subtitle),
            items: items.into(),
            verb: verb.into(),
            verb_info: opt_bytes(verb_info),
            br_name: opt_bytes(br_name),
            br_code,
        }
    }
}

impl<'a> ShowAddress<'a> {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        address: &'a str,
        address_qr: &'a str,
        title: Option<&'a str>,
        subtitle: Option<&'a str>,
        account: Option<&'a str>,
        path: Option<&'a str>,
        xpubs: &'a [Property<'a>],
        chunkify: bool,
        br_code: i32,
        case_sensitive: bool,
    ) -> Self {
        Self {
            address: address.into(),
            address_qr: address_qr.into(),
            title: opt_bytes(title),
            subtitle: opt_bytes(subtitle),
            account: opt_bytes(account),
            path: opt_bytes(path),
            xpubs: xpubs.into(),
            chunkify,
            br_code,
            case_sensitive,
        }
    }
}
