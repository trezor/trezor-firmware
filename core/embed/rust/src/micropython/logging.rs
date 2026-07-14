use sys::syslog::{log, LogLevel};

use crate::micropython::{map::Map, module::Module, obj::Obj, qstr::Qstr};

use crate::{
    error::Error,
    micropython::{buffer::StrBuffer, util},
    util::logger::init_rust_logging,
};

fn _log(level: LogLevel, args: &[Obj], kwargs: &Map) -> Result<Obj, Error> {
    let [module, fmt, fmt_args @ ..] = args else {
        return Err(Error::TypeError);
    };

    let module_name = StrBuffer::try_from(*module)?;

    log(module_name.as_ref(), level, |writer| -> Result<(), Error> {
        if let Ok(iface_obj) = kwargs.get(Qstr::MP_QSTR_iface) {
            if iface_obj != Obj::const_none() {
                let iface_type = iface_obj.type_().ok_or(Error::TypeError)?;
                let iface_prefix = uformat!(len: 128, "\x1b[93m[{}]\x1b[0m ", iface_type.name());
                writer.write(iface_prefix.as_ref());
            }
        }

        let msg: StrBuffer = util::modulo_format(*fmt, fmt_args)?.try_into()?;
        writer.write(msg.as_ref());
        Ok(())
    })?;

    Ok(Obj::const_none())
}

extern "C" fn py_debug(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |args: &[Obj], kwargs: &Map| _log(LogLevel::Debug, args, kwargs);
    unsafe {
        util::try_with_args_and_kwargs(n_args, args, kwargs, block);
    }
    Obj::const_none()
}

extern "C" fn py_info(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |args: &[Obj], kwargs: &Map| _log(LogLevel::Info, args, kwargs);
    unsafe {
        util::try_with_args_and_kwargs(n_args, args, kwargs, block);
    }
    Obj::const_none()
}

extern "C" fn py_warning(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |args: &[Obj], kwargs: &Map| _log(LogLevel::Warn, args, kwargs);
    unsafe {
        util::try_with_args_and_kwargs(n_args, args, kwargs, block);
    }
    Obj::const_none()
}

extern "C" fn py_error(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |args: &[Obj], kwargs: &Map| _log(LogLevel::Error, args, kwargs);
    unsafe {
        util::try_with_args_and_kwargs(n_args, args, kwargs, block);
    }
    Obj::const_none()
}

extern "C" fn py_init(level: Obj) -> Obj {
    let block = || {
        init_rust_logging(level.try_into()?);
        Ok(())
    };
    unsafe {
        util::try_or_raise(block);
    }
    Obj::const_none()
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

    /// def init(level: int) -> None:
    ///     """
    ///     Initialize Rust logging connector.
    ///     """
    Qstr::MP_QSTR_init => obj_fn_1!(py_init).as_obj(),
};
