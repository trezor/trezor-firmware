//! Stable-ABI mirror of `structs.rs`'s UI/progress argument structs.
//!
//! `structs.rs` is the wire IDL shared byte-for-byte with Core's Rust+Python
//! side and isn't itself ABI-stable (`rkyv`-only, not `#[stabby::stabby]`).
//! These mirror types exist purely so the `UiV1` trait can cross the stable
//! ABI boundary; `core/embed/api`'s implementation converts a mirror value
//! into the matching `structs.rs` enum internally before sending it over the
//! wire.
//!
//! Optional string fields are `StabbyOption<Slice<u8>>` (raw bytes), not
//! `StabbyOption<Str>` — `Str` doesn't propagate niche/determinant info
//! through its own `Slice<u8>` wrapper, so `stabby::option::Option<Str<'_>>`
//! fails to satisfy `#[stabby::stabby]`'s `IDeterminantProvider` bound where
//! `Option<Slice<u8>>` (the type `Str` itself wraps) does not have this
//! issue. [`opt_bytes`]/[`as_opt_str`] convert at the edges.

use stabby::option::Option as StabbyOption;
use stabby::slice::Slice;
use stabby::str::Str;

use super::util::FastResult;
use super::wire::WireError;

/// Converts an optional `&str` constructor argument into the
/// niche-friendly `StabbyOption<Slice<u8>>` field representation.
pub(crate) fn opt_bytes(s: Option<&str>) -> StabbyOption<Slice<'_, u8>> {
    s.map(|s| Slice::from(s.as_bytes())).into()
}

/// Recovers the `&str` an [`opt_bytes`]-produced field holds, if any.
///
/// # Safety
///
/// `bytes`, if present, must have come from [`opt_bytes`] applied to a
/// genuine `&str` (true for every field on every type in this module).
pub fn as_opt_str(bytes: StabbyOption<Slice<'_, u8>>) -> Option<&str> {
    core::option::Option::from(bytes).map(|b: Slice<'_, u8>| {
        // SAFETY: see function doc.
        unsafe { core::str::from_utf8_unchecked(b.as_slice()) }
    })
}

/// A key-value pair with an optional monospace flag, used in UI detail views.
#[stabby::stabby]
#[derive(Clone)]
pub struct Property<'a> {
    pub key: Str<'a>,
    pub value: Str<'a>,
    pub mono: bool,
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

/// A string with an optional monospace flag, used in UI list views.
#[stabby::stabby]
#[derive(Clone)]
pub struct StrExt<'a> {
    pub key: Str<'a>,
    pub mono: bool,
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

/// Result returned by Core after a UI interaction.
#[stabby::stabby]
#[repr(C, u8)]
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum TrezorUiResult {
    Confirmed,
    Back,
    Cancelled,
    Info,
    Integer(u32),
}

/// A menu of selectable string items.
#[stabby::stabby]
#[derive(Clone)]
pub struct SelectMenu<'a> {
    pub items: Slice<'a, Str<'a>>,
    pub cancel: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
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

#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmTrade<'a> {
    pub title: Str<'a>,
    pub subtitle: Str<'a>,
    pub buy: Str<'a>,
    pub sell: StabbyOption<Slice<'a, u8>>,
    pub back_button: bool,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
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

#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmAction<'a> {
    pub title: Str<'a>,
    pub action: Str<'a>,
    pub description: StabbyOption<Slice<'a, u8>>,
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    pub hold: bool,
    pub cancel: bool,
    pub verb: StabbyOption<Slice<'a, u8>>,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
    pub external_menu: bool,
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

#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmSummary<'a> {
    pub title: Str<'a>,
    pub amount: StabbyOption<Slice<'a, u8>>,
    pub amount_label: StabbyOption<Slice<'a, u8>>,
    pub fee: Str<'a>,
    pub fee_label: Str<'a>,
    pub account_title: StabbyOption<Slice<'a, u8>>,
    pub account_items: StabbyOption<Slice<'a, Property<'a>>>,
    pub extra_title: StabbyOption<Slice<'a, u8>>,
    pub extra_items: StabbyOption<Slice<'a, Property<'a>>>,
    pub back_button: bool,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
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

/// Fields mirror [`crate::structs::ConfirmValue`] except `footer`, which is
/// flattened into `footer_text`/`footer_bold` since stabby has no tuples;
/// [`Self::new`] still takes the same `Option<(&str, bool)>` shape as the
/// wire-format constructor, since a plain (non-ABI-crossing) parameter can
/// be a tuple.
#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmValue<'a> {
    pub title: Str<'a>,
    pub value: Str<'a>,
    pub description: StabbyOption<Slice<'a, u8>>,
    pub is_data: bool,
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    pub verb: StabbyOption<Slice<'a, u8>>,
    pub info: bool,
    pub hold: bool,
    pub chunkify: bool,
    pub page_counter: bool,
    pub cancel: bool,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
    pub external_menu: bool,
    pub footer_text: StabbyOption<Slice<'a, u8>>,
    pub footer_bold: bool,
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

#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmValueIntro<'a> {
    pub title: Str<'a>,
    pub value: Str<'a>,
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    pub verb: StabbyOption<Slice<'a, u8>>,
    pub verb_cancel: StabbyOption<Slice<'a, u8>>,
    pub verb_view_all: StabbyOption<Slice<'a, u8>>,
    pub hold: bool,
    pub chunkify: bool,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
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

#[stabby::stabby]
#[derive(Clone)]
pub struct ShowWarning<'a> {
    pub title: Str<'a>,
    pub content: Str<'a>,
    pub verb: Str<'a>,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
    pub allow_cancel: bool,
    pub danger: bool,
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

#[stabby::stabby]
#[derive(Clone)]
pub struct ShowMismatch<'a> {
    pub title: Str<'a>,
    pub br_code: i32,
}

impl<'a> ShowMismatch<'a> {
    pub fn new(title: &'a str, br_code: i32) -> Self {
        Self {
            title: title.into(),
            br_code,
        }
    }
}

#[stabby::stabby]
#[derive(Clone)]
pub struct ShowDanger<'a> {
    pub title: Str<'a>,
    pub content: Str<'a>,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
    pub verb_cancel: StabbyOption<Slice<'a, u8>>,
    pub menu_title: StabbyOption<Slice<'a, u8>>,
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

#[stabby::stabby]
#[derive(Clone)]
pub struct ShowSuccess<'a> {
    pub title: Str<'a>,
    pub content: Str<'a>,
    pub button: Str<'a>,
    pub duration_ms: StabbyOption<u32>,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
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

#[stabby::stabby]
#[derive(Clone)]
pub struct RequestNumber<'a> {
    pub title: Str<'a>,
    pub content: Str<'a>,
    pub initial: u32,
    pub min: u32,
    pub max: u32,
    pub br_code: i32,
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

#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmProperties<'a> {
    pub title: Str<'a>,
    pub props: Slice<'a, Property<'a>>,
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    pub verb: StabbyOption<Slice<'a, u8>>,
    pub hold: bool,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
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

#[stabby::stabby]
#[derive(Clone)]
pub struct ShowProperties<'a> {
    pub title: Str<'a>,
    pub props: Slice<'a, Property<'a>>,
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
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

#[stabby::stabby]
#[derive(Clone)]
pub struct ShowPublicKey<'a> {
    pub pubkey: Str<'a>,
    pub title: Str<'a>,
    pub account: StabbyOption<Slice<'a, u8>>,
    pub path: StabbyOption<Slice<'a, u8>>,
    pub warning: StabbyOption<Slice<'a, u8>>,
    pub br_name: Str<'a>,
    pub br_code: i32,
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

#[stabby::stabby]
#[derive(Clone)]
pub struct ShowInfoWithCancel<'a> {
    pub title: Str<'a>,
    pub items: Slice<'a, Property<'a>>,
    pub chunkify: bool,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
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

#[stabby::stabby]
#[derive(Clone)]
pub struct ConfirmWithInfo<'a> {
    pub title: Str<'a>,
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    pub items: Slice<'a, StrExt<'a>>,
    pub verb: Str<'a>,
    pub verb_info: StabbyOption<Slice<'a, u8>>,
    pub br_name: StabbyOption<Slice<'a, u8>>,
    pub br_code: i32,
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

#[stabby::stabby]
#[derive(Clone)]
pub struct ShowAddress<'a> {
    pub address: Str<'a>,
    pub address_qr: Str<'a>,
    pub title: StabbyOption<Slice<'a, u8>>,
    pub subtitle: StabbyOption<Slice<'a, u8>>,
    pub account: StabbyOption<Slice<'a, u8>>,
    pub path: StabbyOption<Slice<'a, u8>>,
    pub xpubs: Slice<'a, Property<'a>>,
    pub chunkify: bool,
    pub br_code: i32,
    pub case_sensitive: bool,
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

/// Talks to Core's UI/progress screens. Each method sends one screen request
/// over the wire and returns Core's response — implemented in `core/embed/api`
/// against [`super::wire::WireV1`].
#[stabby::stabby(checked)]
pub trait UiV1: Send + Sync {
    extern "C" fn confirm_value<'a>(
        &self,
        value: ConfirmValue<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn confirm_value_intro<'a>(
        &self,
        value: ConfirmValueIntro<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn confirm_summary<'a>(
        &self,
        value: ConfirmSummary<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn confirm_action<'a>(
        &self,
        value: ConfirmAction<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn select_menu<'a>(
        &self,
        value: SelectMenu<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn confirm_properties<'a>(
        &self,
        value: ConfirmProperties<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn show_properties<'a>(
        &self,
        value: ShowProperties<'a>,
    ) -> FastResult<(), WireError>;
    extern "C" fn show_warning<'a>(&self, value: ShowWarning<'a>) -> FastResult<(), WireError>;
    extern "C" fn show_info_with_cancel<'a>(
        &self,
        value: ShowInfoWithCancel<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn show_mismatch<'a>(
        &self,
        value: ShowMismatch<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn confirm_trade<'a>(
        &self,
        value: ConfirmTrade<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn show_danger<'a>(
        &self,
        value: ShowDanger<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn show_success<'a>(&self, value: ShowSuccess<'a>) -> FastResult<(), WireError>;
    extern "C" fn request_number<'a>(
        &self,
        value: RequestNumber<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn show_public_key<'a>(
        &self,
        value: ShowPublicKey<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn confirm_with_info<'a>(
        &self,
        value: ConfirmWithInfo<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;
    extern "C" fn show_address<'a>(
        &self,
        value: ShowAddress<'a>,
    ) -> FastResult<TrezorUiResult, WireError>;

    extern "C" fn init_progress<'a>(
        &self,
        description: StabbyOption<Slice<'a, u8>>,
        title: StabbyOption<Slice<'a, u8>>,
        indeterminate: bool,
        danger: bool,
    ) -> FastResult<(), WireError>;
    extern "C" fn update_progress<'a>(
        &self,
        description: StabbyOption<Slice<'a, u8>>,
        value: u32,
    ) -> FastResult<(), WireError>;
    extern "C" fn end_progress(&self) -> FastResult<(), WireError>;
}

pub type UiV1Vtable = stabby::vtable!(UiV1 + Send + Sync);
pub type UiV1Ref<'a> = stabby::DynRef<'a, UiV1Vtable>;
pub type StaticUiV1 = UiV1Ref<'static>;
