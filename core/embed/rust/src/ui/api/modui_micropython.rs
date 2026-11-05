//! `trezormodui`: the screens of `modui` and the wire of an app's UI requests,
//! for core's `trezor.ui.modui` and the extapp driver.
//!
//! The screens take the facts as plain Python values and draw them with the
//! model's [`ModUI`]. The wire half reads an app's request into the same plain
//! values and encodes core's answers back. Every number the two sides share
//! comes from `trezor_app_sdk::structs` and is exported here, so Python keeps
//! no copies of its own.

use rkyv::option::ArchivedOption;
use rkyv::rancor::Failure;
use rkyv::Archived;
use trezor_app_sdk::structs::{
    Answer, FieldKind, Slice, StrSlice, TrezorProgressEnum, TrezorUiEnum, TrezorUiResult,
    UiChunkRequest, WireExtra, WireField, MAX_DATA_FIELDS, UI_MSG_CHUNK, UI_MSG_CHUNK_FAILED,
    UI_MSG_DECISION,
};

use crate::micropython::buffer::get_buffer;
use crate::micropython::list::List;
use crate::micropython::macros::{obj_fn_1, obj_fn_kw, obj_module};
use crate::micropython::map::Map;
use crate::micropython::module::Module;
use crate::micropython::qstr::Qstr;
use crate::micropython::tuple::Tuple;
use crate::micropython::{util, Error, Obj};
use crate::strutil::TString;
use crate::ui::ui_modui::{Fields, ModUI};
use crate::ui::ModelUI;

extern "C" fn new_review(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let fields = Fields::new(kwargs.get(Qstr::MP_QSTR_fields)?)?;
        let verb: Option<TString> = kwargs
            .get(Qstr::MP_QSTR_verb)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let hold: bool = kwargs.get_or(Qstr::MP_QSTR_hold, false)?;
        let menu: bool = kwargs.get_or(Qstr::MP_QSTR_menu, false)?;
        Ok(ModelUI::review(title, fields, verb, hold, menu)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_extra(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let fields = Fields::new(kwargs.get(Qstr::MP_QSTR_fields)?)?;
        Ok(ModelUI::extra(title, fields)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_danger(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let fields = Fields::new(kwargs.get(Qstr::MP_QSTR_fields)?)?;
        Ok(ModelUI::danger(title, fields)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

/// The arguments both verifications take: the value, the account, the path
/// and the ButtonRequest's name.
fn verify_args(
    kwargs: &Map,
    value: Qstr,
) -> Result<
    (
        TString<'static>,
        Option<TString<'static>>,
        Option<TString<'static>>,
        TString<'static>,
    ),
    Error,
> {
    let optional = |key| -> Result<Option<TString<'static>>, Error> {
        kwargs
            .get(key)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()
    };
    Ok((
        kwargs.get(value)?.try_into()?,
        optional(Qstr::MP_QSTR_account)?,
        optional(Qstr::MP_QSTR_path)?,
        kwargs.get(Qstr::MP_QSTR_br_name)?.try_into()?,
    ))
}

extern "C" fn new_verify_address(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let (address, account, path, br_name) = verify_args(kwargs, Qstr::MP_QSTR_address)?;
        Ok(ModelUI::verify_address(address, account, path, br_name)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_verify_pubkey(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let (pubkey, account, path, br_name) = verify_args(kwargs, Qstr::MP_QSTR_pubkey)?;
        Ok(ModelUI::verify_pubkey(pubkey, account, path, br_name)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_done(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = move |_args: &[Obj], kwargs: &Map| {
        let text: TString = kwargs.get(Qstr::MP_QSTR_text)?.try_into()?;
        let time_ms: u32 = kwargs.get_or(Qstr::MP_QSTR_time_ms, 0)?;
        Ok(ModelUI::done(text, time_ms)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_max_extras(answer: Obj) -> Obj {
    let block = || {
        let answer = Answer::try_from(u8::try_from(answer)?)
            .map_err(|_| Error::ValueError(c"unknown answer"))?;
        Ok(Obj::small_int(answer.max_extras() as u16))
    };
    unsafe { util::try_or_raise(block) }
}

fn opt_obj(s: &ArchivedOption<Archived<StrSlice>>) -> Result<Obj, Error> {
    match s.as_ref() {
        Some(s) => Obj::try_from(s.as_ref()),
        None => Ok(Obj::const_none()),
    }
}

/// The wire's kind, as the screens read it back.
fn field_kind(kind: &Archived<FieldKind>) -> FieldKind {
    match kind {
        Archived::<FieldKind>::Text => FieldKind::Text,
        Archived::<FieldKind>::Amount => FieldKind::Amount,
        Archived::<FieldKind>::Address => FieldKind::Address,
        Archived::<FieldKind>::Data => FieldKind::Data,
        Archived::<FieldKind>::Note => FieldKind::Note,
        Archived::<FieldKind>::Warning => FieldKind::Warning,
    }
}

fn answer(answer: &Archived<Answer>) -> Answer {
    match answer {
        Archived::<Answer>::Confirm => Answer::Confirm,
        Archived::<Answer>::Strong => Answer::Strong,
        Archived::<Answer>::Danger => Answer::Danger,
        Archived::<Answer>::Details => Answer::Details,
    }
}

/// One fact of a request, as `(kind, label, value, ticker)`: `label` is `None`
/// for notes and warnings, `value` is `str` for the text kinds and the total
/// length for `Data`, whose bytes the driver pulls from the app while the
/// person pages, and `ticker` is an amount's unit, `None` for the other kinds.
fn obj_from_field(field: &Archived<WireField<'_>>) -> Result<Obj, Error> {
    let kind = field_kind(&field.kind);
    let value = if kind == FieldKind::Data {
        Obj::try_from(field.len.to_native())?
    } else {
        let text = core::str::from_utf8(field.value.as_ref())
            .map_err(|_| Error::ValueError(c"Invalid UI message"))?;
        Obj::try_from(text)?
    };
    Obj::try_from((
        Obj::small_int(kind as u16),
        opt_obj(&field.label)?,
        value,
        opt_obj(&field.ticker)?,
    ))
}

fn obj_from_fields(archived: &Archived<Slice<'_, WireField<'_>>>) -> Result<Obj, Error> {
    let slice = archived.as_ref();
    let mut list = List::with_capacity(slice.len())?;
    for field in slice {
        list.append(obj_from_field(field)?)?;
    }
    Ok(list.leak().into())
}

fn obj_from_extras(archived: &Archived<Slice<'_, WireExtra<'_>>>) -> Result<Obj, Error> {
    let slice = archived.as_ref();
    let mut list = List::with_capacity(slice.len())?;
    for extra in slice {
        list.append(Obj::try_from((
            Obj::try_from(extra.label.as_ref())?,
            obj_from_fields(&extra.fields)?,
        ))?)?;
    }
    Ok(list.leak().into())
}

extern "C" fn new_deserialize_ui_message(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let obj: Obj = kwargs.get(Qstr::MP_QSTR_data)?;
        let archived = rkyv::access::<Archived<TrezorUiEnum>, Failure>(unsafe { get_buffer(obj) }?)
            .map_err(|_| Error::ValueError(c"Invalid UI message"))?;

        let fields: &[Obj] = match archived {
            Archived::<TrezorUiEnum>::Review(m) => &[
                Obj::small_int(TrezorUiEnum::REVIEW),
                Obj::try_from(m.step.as_ref())?,
                Obj::try_from(m.title.as_ref())?,
                obj_from_fields(&m.fields)?,
                obj_from_extras(&m.extras)?,
                Obj::small_int(answer(&m.answer) as u16),
            ],
            Archived::<TrezorUiEnum>::VerifyAddress(m) => &[
                Obj::small_int(TrezorUiEnum::VERIFY_ADDRESS),
                Obj::try_from(m.step.as_ref())?,
                Obj::try_from(m.value.as_ref())?,
                opt_obj(&m.account)?,
                opt_obj(&m.path)?,
            ],
            Archived::<TrezorUiEnum>::VerifyPubkey(m) => &[
                Obj::small_int(TrezorUiEnum::VERIFY_PUBKEY),
                Obj::try_from(m.step.as_ref())?,
                Obj::try_from(m.value.as_ref())?,
                opt_obj(&m.account)?,
                opt_obj(&m.path)?,
            ],
            Archived::<TrezorUiEnum>::Done(m) => &[
                Obj::small_int(TrezorUiEnum::DONE),
                Obj::try_from(m.step.as_ref())?,
                Obj::try_from(m.text.as_ref())?,
            ],
        };
        Ok(Tuple::alloc(fields)?.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_encode_ui_result(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let result: u8 = kwargs.get(Qstr::MP_QSTR_result)?.try_into()?;
        let msg = [
            TrezorUiResult::Confirmed,
            TrezorUiResult::Cancelled,
            TrezorUiResult::ShowDetails,
        ]
        .into_iter()
        .find(|known| *known as u8 == result)
        .ok_or(Error::ValueError(c"unknown UI result"))?;
        crate::util::archive::to_bytes_obj(&msg)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_encode_chunk_request(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let msg = UiChunkRequest {
            field: kwargs.get(Qstr::MP_QSTR_field)?.try_into()?,
            offset: kwargs.get(Qstr::MP_QSTR_offset)?.try_into()?,
            len: kwargs.get(Qstr::MP_QSTR_length)?.try_into()?,
        };
        crate::util::archive::to_bytes_obj(&msg)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_deserialize_progress_message(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let obj: Obj = kwargs.get(Qstr::MP_QSTR_data)?;
        let archived =
            rkyv::access::<Archived<TrezorProgressEnum>, Failure>(unsafe { get_buffer(obj) }?)
                .map_err(|_| Error::ValueError(c"Invalid progress message"))?;
        Ok(match archived {
            Archived::<TrezorProgressEnum>::Init { label, total } => (
                Obj::try_from(label.as_ref())?,
                Obj::try_from(total.to_native())?,
            )
                .try_into()?,
            Archived::<TrezorProgressEnum>::Step { units } => Obj::try_from(units.to_native())?,
            Archived::<TrezorProgressEnum>::Label { label } => Obj::try_from(label.as_ref())?,
            Archived::<TrezorProgressEnum>::End => Obj::const_none(),
        })
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
#[rustfmt::skip]
pub static mp_module_trezormodui: Module = obj_module! {
    /// from trezorui_api import LayoutObj, UiResult
    ///
    /// # A fact as the screens take it: `(kind, label, value)`, with the
    /// # page's chunk as the value of a `Data` field.
    /// Field = tuple[int, str | None, str | bytes]
    /// mock:global
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezormodui.to_obj(),

    /// TEXT: int
    Qstr::MP_QSTR_TEXT => Obj::small_int(FieldKind::Text as u16),

    /// AMOUNT: int
    Qstr::MP_QSTR_AMOUNT => Obj::small_int(FieldKind::Amount as u16),

    /// ADDRESS: int
    Qstr::MP_QSTR_ADDRESS => Obj::small_int(FieldKind::Address as u16),

    /// DATA: int
    Qstr::MP_QSTR_DATA => Obj::small_int(FieldKind::Data as u16),

    /// NOTE: int
    Qstr::MP_QSTR_NOTE => Obj::small_int(FieldKind::Note as u16),

    /// WARNING: int
    Qstr::MP_QSTR_WARNING => Obj::small_int(FieldKind::Warning as u16),

    /// CONFIRM: int
    Qstr::MP_QSTR_CONFIRM => Obj::small_int(Answer::Confirm as u16),

    /// STRONG: int
    Qstr::MP_QSTR_STRONG => Obj::small_int(Answer::Strong as u16),

    /// DANGER: int
    Qstr::MP_QSTR_DANGER => Obj::small_int(Answer::Danger as u16),

    /// DETAILS: int
    Qstr::MP_QSTR_DETAILS => Obj::small_int(Answer::Details as u16),

    /// MAX_DATA_FIELDS: int
    Qstr::MP_QSTR_MAX_DATA_FIELDS => Obj::small_int(MAX_DATA_FIELDS as u16),

    /// def max_extras(answer: int) -> int:
    ///     """How many extras a review with this answer may offer: what is left
    ///     of the menu's entries after the answer's own."""
    Qstr::MP_QSTR_max_extras => obj_fn_1!(new_max_extras).as_obj(),

    /// def review(
    ///     *,
    ///     title: str,
    ///     fields: Sequence[Field],
    ///     verb: str | None = None,
    ///     hold: bool = False,
    ///     menu: bool = False,
    /// ) -> LayoutObj[UiResult]:
    ///     """One page of a review. The model picks the screen from the facts.
    ///     With `menu`, a menu button answers `INFO` and the way out lives in
    ///     the menu; without it the screen offers its own."""
    Qstr::MP_QSTR_review => obj_fn_kw!(0, new_review).as_obj(),

    /// def extra(
    ///     *,
    ///     title: str,
    ///     fields: Sequence[Field],
    /// ) -> LayoutObj[UiResult]:
    ///     """One page of an extra: read-only, left without a decision."""
    Qstr::MP_QSTR_extra => obj_fn_kw!(0, new_extra).as_obj(),

    /// def danger(
    ///     *,
    ///     title: str,
    ///     fields: Sequence[Field],
    /// ) -> LayoutObj[UiResult]:
    ///     """One page of a danger: refusing is the default."""
    Qstr::MP_QSTR_danger => obj_fn_kw!(0, new_danger).as_obj(),

    /// def verify_address(
    ///     *,
    ///     address: str,
    ///     account: str | None = None,
    ///     path: str | None = None,
    ///     br_name: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """The person's own address to check; the screen sends its own
    ///     ButtonRequest."""
    Qstr::MP_QSTR_verify_address => obj_fn_kw!(0, new_verify_address).as_obj(),

    /// def verify_pubkey(
    ///     *,
    ///     pubkey: str,
    ///     account: str | None = None,
    ///     path: str | None = None,
    ///     br_name: str,
    /// ) -> LayoutObj[UiResult]:
    ///     """The person's own public key to check; the screen sends its own
    ///     ButtonRequest."""
    Qstr::MP_QSTR_verify_pubkey => obj_fn_kw!(0, new_verify_pubkey).as_obj(),

    /// def done(
    ///     *,
    ///     text: str,
    ///     time_ms: int = 0,
    /// ) -> LayoutObj[UiResult]:
    ///     """The flow is finished. Goes away after `time_ms`, or on a tap when
    ///     it is 0."""
    Qstr::MP_QSTR_done => obj_fn_kw!(0, new_done).as_obj(),

    /// REQUEST_REVIEW: int
    Qstr::MP_QSTR_REQUEST_REVIEW => Obj::small_int(TrezorUiEnum::REVIEW),

    /// REQUEST_VERIFY_ADDRESS: int
    Qstr::MP_QSTR_REQUEST_VERIFY_ADDRESS => Obj::small_int(TrezorUiEnum::VERIFY_ADDRESS),

    /// REQUEST_VERIFY_PUBKEY: int
    Qstr::MP_QSTR_REQUEST_VERIFY_PUBKEY => Obj::small_int(TrezorUiEnum::VERIFY_PUBKEY),

    /// REQUEST_DONE: int
    Qstr::MP_QSTR_REQUEST_DONE => Obj::small_int(TrezorUiEnum::DONE),

    /// RESULT_CONFIRMED: int
    Qstr::MP_QSTR_RESULT_CONFIRMED => Obj::small_int(TrezorUiResult::Confirmed as u16),

    /// RESULT_CANCELLED: int
    Qstr::MP_QSTR_RESULT_CANCELLED => Obj::small_int(TrezorUiResult::Cancelled as u16),

    /// RESULT_SHOW_DETAILS: int
    Qstr::MP_QSTR_RESULT_SHOW_DETAILS => Obj::small_int(TrezorUiResult::ShowDetails as u16),

    /// MSG_DECISION: int
    Qstr::MP_QSTR_MSG_DECISION => Obj::small_int(UI_MSG_DECISION),

    /// MSG_CHUNK: int
    Qstr::MP_QSTR_MSG_CHUNK => Obj::small_int(UI_MSG_CHUNK),

    /// MSG_CHUNK_FAILED: int
    Qstr::MP_QSTR_MSG_CHUNK_FAILED => Obj::small_int(UI_MSG_CHUNK_FAILED),

    /// PROGRESS_INIT: int
    Qstr::MP_QSTR_PROGRESS_INIT => Obj::small_int(TrezorProgressEnum::INIT),

    /// PROGRESS_STEP: int
    Qstr::MP_QSTR_PROGRESS_STEP => Obj::small_int(TrezorProgressEnum::STEP),

    /// PROGRESS_LABEL: int
    Qstr::MP_QSTR_PROGRESS_LABEL => Obj::small_int(TrezorProgressEnum::LABEL),

    /// PROGRESS_END: int
    Qstr::MP_QSTR_PROGRESS_END => Obj::small_int(TrezorProgressEnum::END),

    /// def deserialize_ui_message(
    ///     *,
    ///     data: bytes,
    /// ) -> tuple[Any, ...]:
    ///     """Read an app's UI request into plain data. The first element is the
    ///     request's kind (`REQUEST_*`) and the second its step; a review goes on
    ///     with `(title, fields, extras, answer)`, a verification with `(value,
    ///     account, path)` and a done with `(text,)`. `fields` is a list of
    ///     `(kind, label, value, ticker)` whose `Data` value is its total
    ///     length, and `extras` is a list of `(label, fields)`."""
    Qstr::MP_QSTR_deserialize_ui_message => obj_fn_kw!(0, new_deserialize_ui_message).as_obj(),

    /// def encode_ui_result(
    ///     *,
    ///     result: int,
    /// ) -> bytes:
    ///     """Serialize a decision (`RESULT_*`) into the bytes sent back to the
    ///     app."""
    Qstr::MP_QSTR_encode_ui_result => obj_fn_kw!(0, new_encode_ui_result).as_obj(),

    /// def encode_chunk_request(
    ///     *,
    ///     field: int,
    ///     offset: int,
    ///     length: int,
    /// ) -> bytes:
    ///     """Serialize a request for one chunk of a `Data` field: its flat index,
    ///     the offset and the length."""
    Qstr::MP_QSTR_encode_chunk_request => obj_fn_kw!(0, new_encode_chunk_request).as_obj(),

    /// def deserialize_progress_message(
    ///     *,
    ///     data: bytes,
    /// ) -> Any:
    ///     """Read an app's progress message: `(label, total)` for a start, the
    ///     units for a step, the label for a change of label, `None` for the
    ///     end."""
    Qstr::MP_QSTR_deserialize_progress_message => obj_fn_kw!(0, new_deserialize_progress_message).as_obj(),
};
