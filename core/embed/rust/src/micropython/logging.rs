use core::str::from_utf8;

use crate::{
    error::Error,
    micropython::{
        buffer::StrBuffer, map::Map, module::Module, obj::Obj, print::print, qstr::Qstr, util,
    },
    strutil,
    trezorhal::time::ticks_ms,
};

fn _log(level: &str, args: &[Obj], kwargs: &Map) -> Result<Obj, Error> {
    let [module, fmt, fmt_args @ ..] = args else {
        return Err(Error::TypeError);
    };
    {
        let millis = ticks_ms();
        let seconds = millis / 1000;
        let mut millis_str = [b'0'; 3];
        let len = unwrap!(strutil::format_i64((millis % 1000).into(), &mut millis_str)).len();
        millis_str.rotate_left(len);
        let log_prefix = uformat!(len: 128, "{}.{} \x1b[35m{}\x1b[0m \x1b[{}\x1b[0m ",
            seconds, unwrap!(from_utf8(&millis_str)), StrBuffer::try_from(*module)?.as_ref(), level,
        );
        print(&log_prefix);
    }

    if let Ok(iface_obj) = kwargs.get(Qstr::MP_QSTR_iface) {
        if iface_obj != Obj::const_none() {
            let iface_type = iface_obj.type_().ok_or(Error::TypeError)?;
            let iface_prefix = uformat!(len: 128, "\x1b[93m[{}]\x1b[0m ", iface_type.name());
            print(&iface_prefix);
        }
    }

    let msg: StrBuffer = util::modulo_format(*fmt, fmt_args)?.try_into()?;
    print(msg.as_ref());
    print("\n");
    Ok(Obj::const_none())
}

extern "C" fn py_debug(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |args: &[Obj], kwargs: &Map| _log("32mDEBUG", args, kwargs);
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn py_info(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |args: &[Obj], kwargs: &Map| _log("36mINFO", args, kwargs);
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn py_warning(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |args: &[Obj], kwargs: &Map| _log("33mWARNING", args, kwargs);
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn py_error(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |args: &[Obj], kwargs: &Map| _log("31mERROR", args, kwargs);
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
#[rustfmt::skip]
pub static mp_module_trezorlog: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorlog.to_obj(),

    /// mock:global

    /// def debug(name: str, msg: str, *args: Any, *, iface: WireInterface | None = None) -> None:
    ///     ...
    Qstr::MP_QSTR_debug => obj_fn_kw!(2, py_debug).as_obj(),

    /// def info(name: str, msg: str, *args: Any, *, iface: WireInterface | None = None) -> None:
    ///     ...
    Qstr::MP_QSTR_info => obj_fn_kw!(2, py_info).as_obj(),

    /// def warning(name: str, msg: str, *args: Any, *, iface: WireInterface | None = None) -> None:
    ///     ...
    Qstr::MP_QSTR_warning => obj_fn_kw!(2, py_warning).as_obj(),

    /// def error(name: str, msg: str, *args: Any, *, iface: WireInterface | None = None) -> None:
    ///     ...
    Qstr::MP_QSTR_error => obj_fn_kw!(2, py_error).as_obj(),
};
