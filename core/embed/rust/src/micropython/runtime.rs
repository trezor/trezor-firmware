use core::mem::MaybeUninit;

use crate::error::Error;

use super::ffi;

/// Raise a micropython exception via NLR jump.
/// Jumps directly out of the context without running any destructors,
/// finalizers, etc. This is very likely to break a lot of Rust's assumptions:
/// in particular, _any_ jumping over Rust code is currently considered
/// undefined. See full discussion at https://github.com/rust-lang/rfcs/issues/2625
/// Should only be called at the boundary which would otherwise return to C.
pub unsafe fn raise_exception(err: Error) -> ! {
    unsafe {
        // SAFETY:
        // - argument must be an exception instance
        // (err.into_obj() should return the right thing)
        ffi::nlr_jump(err.into_obj().as_ptr());
    }
}

/// Execute `func` while catching MicroPython exceptions. Returns `Ok` in the
/// successful case, and `Err` with the caught `Obj` in case of a raise.
///
/// # Safety
///
/// Not intended to be called directly. Use [`catch_exception!`] macro instead.
///
/// Typically, the body of `func` will call a function that may raise. When it
/// does, the NLR jump skips over the rest of the closure, which includes any
/// Drop impls and possibly other finalizing code. _Any_ jumping over Rust code
/// is currently considered undefined, see also [`raise_exception`].
///
/// The only acceptable contents of the `func` closure is a single call to a FFI
/// function that may raise. All other Rust code, incl. type conversions, should
/// be placed outside `func`.
pub(crate) unsafe fn _catch_exception_dangerous_do_not_call_directly<F, T>(mut func: F) -> Result<T, Error>
where
    F: FnMut() -> T,
{
    // Because MicroPython exceptions use `setjmp` and `longjmp`-like mechanism that
    // doesn't play too well with Rust, we setup the non-local return pads in C, and
    // execute `func` through a callback.

    unsafe {
        // First, we craft a wrapping closure that calls `func`. Because we are generic
        // over the return type, we cannot pass the returned value over the FFI
        // boundary, so we assign it explicitly in `wrapper`.
        let mut result = MaybeUninit::zeroed();
        let mut wrapper = || {
            result.write(func());
        };
        // `wrapper` is a closure, and to pass it over the FFI, we split it into a
        // function pointer, and a user-data pointer.
        // `ffi::trezor_obj_call_protected` then calls the `callback` with the
        // `argument`.
        let (callback, argument) = split_func_into_callback_and_argument(&mut wrapper);
        let exception = ffi::trezor_obj_call_protected(Some(callback), argument);
        if exception.is_null() {
            Ok(result.assume_init())
        } else {
            Err(Error::CaughtException(exception))
        }
    }
}

/// Catch a MicroPython exception correctly.
///
/// This macro safely wraps the functionality of
/// [`_catch_exception_dangerous_do_not_call_directly`]. As its argument, it
/// expects a function name (more specifically, an expression that evaluates to
/// a function item) and optionally a list of its arguments enclosed in curly
/// braces.
///
/// The function item will typically be a FFI call to MicroPython C API that can
/// raise an exception.
///
/// Internally, the macro will force all arguments to be evaluated, then
/// generate a closure that only calls the given function with the evaluated
/// arguments and then returns.
///
/// # Examples
///
/// ```
/// let result = catch_exception!(safe_func_no_args);
/// let result2 = catch_exception!(safe_func_no_args => { })?;
/// catch_exception!(unsafe { ffi::mp_obj_list_append } => { list, value })?;
/// ```
///
/// # Safety
///
/// While the invocation itself is safe, it will typically be invoking an unsafe
/// function. For this reason, there is an "unsafe" spelling of the macro:
///
/// ```
/// // Invocation of an unsafe function with safe arguments
/// let result = catch_exception!(unsafe { unsafe_func } => { arg0, arg1 });
/// ```
///
/// Invoking this way, a generated `unsafe` block will only cover the call of
/// the unsafe function itself, but neither the macro invocation nor the
/// argument expressions.
///
/// Placing the whole macro in an `unsafe` block also covers the unsafe function
/// invocation, so the use of the internal `unsafe` is optional.
macro_rules! catch_exception {
    // TERMINAL RULE: implementation of the safe catch_exception call
    (@real safe $func:expr => { $($name:ident: $arg:expr,)* }) => {{
        // evaluate the arguments
        $(let $name = $arg;)*
        // generate a closure
        let closure = || { $func($($name),*) };
        // call the closure
        #[allow(unused_unsafe)]
        unsafe { $crate::micropython::runtime::_catch_exception_dangerous_do_not_call_directly(closure) }
    }};

    // TERMINAL RULE: implementation of the unsafe catch_exception call
    (@real not_safe $func:expr => { $($name:ident: $arg:expr,)* }) => {{
        // evaluate the arguments
        $(let $name = $arg;)*
        // generate a closure
        let closure = || unsafe { $func($($name),*) };
        // call the closure
        #[allow(unused_unsafe)]
        unsafe { $crate::micropython::runtime::_catch_exception_dangerous_do_not_call_directly(closure) }
    }};

    // zip expansion: {$arg, ...}
    (@zip $kind:ident $func:expr => { $arg:expr, $($nextarg:tt)* } { $name:ident $($nextname:ident)* } { $($collected:tt)* }) => {
        $crate::micropython::runtime::catch_exception!(@zip $kind $func => { $($nextarg)* } { $($nextname)* } { $($collected)* $name: $arg, })
    };
    // zip terminator: {}
    (@zip $kind:ident $func:expr => { } { $name:ident $($nextname:ident)* } { $($collected:tt)* }) => {
        $crate::micropython::runtime::catch_exception!(@real $kind $func => { $($collected)* })
    };

    // start of the zip, with a list of new names
    (@start $kind:ident $func:expr => { $($arg:expr,)* }) => {
        $crate::micropython::runtime::catch_exception!(
            @zip $kind $func =>
                { $($arg,)* }
                { _a _b _c _d _e _f _g _h _i _j _k _l _m _n _o _p _q _r _s _t _u _v _w _x _y _z }
                { }
        )
    };

    // INVOCATION RULE: call of unsafe function $func ($arg0, $arg1, $arg2) (no trailing comma)
    (unsafe { $func:expr } => { $($arg:expr),* }) => {
        $crate::micropython::runtime::catch_exception!(@start not_safe $func => { $($arg,)* })
    };
    // INVOCATION RULE: call of unsafe function $func ($arg0, $arg1, $arg2,) (trailing comma)
    (unsafe { $func:expr } => { $($arg:expr,)* }) => {
        $crate::micropython::runtime::catch_exception!(@start not_safe $func => { $($arg,)* })
    };
    // INVOCATION RULE: call of safe function $func ($arg0, $arg1, $arg2) (no trailing comma)
    ($func:expr => { $($arg:expr),* }) => {
        $crate::micropython::runtime::catch_exception!(@start safe $func => { $($arg,)* })
    };
    // INVOCATION RULE: call of safe function $func ($arg0, $arg1, $arg2,) (trailing comma)
    ($func:expr => { $($arg:expr,)* }) => {
        $crate::micropython::runtime::catch_exception!(@start safe $func => { $($arg,)* })
    };

    // INVOCATION RULES: call of $func (no arguments)
    (unsafe { $func:expr }) => { $crate::micropython::runtime::catch_exception!(@real not_safe $func => { }) };
    ($func:expr) => { $crate::micropython::runtime::catch_exception!(@real safe $func => { }) };

}

pub(crate) use catch_exception;

type ProtectedArgument = *mut cty::c_void;
type ProtectedCallback = unsafe extern "C" fn(ProtectedArgument);

fn split_func_into_callback_and_argument<F>(func: &mut F) -> (ProtectedCallback, ProtectedArgument)
where
    F: FnMut(),
{
    // Here we mono-morphize a version of `trampoline` for each type `F`, so it
    // calls the correct `FnMut` impl, and cast `func` into its data part to use
    // as the argument.
    (trampoline::<F>, func as *mut _ as *mut _)
}

unsafe extern "C" fn trampoline<F>(arg: ProtectedArgument)
where
    F: FnMut(),
{
    // Synthesize a callable `*mut F` from the closure environment pointer `arg`,
    // and call it.
    let func = arg as *mut F;
    unsafe {
        (*func)();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn safe_func() -> i32 {
        1
    }

    unsafe fn unsafe_func() -> i32 {
        2
    }

    #[test]
    fn catch_exception_safe() {
        let result = catch_exception!(safe_func);
        assert!(matches!(result, Ok(1)));
    }

    #[test]
    fn catch_exception_unsafe() {
        let result = catch_exception!(unsafe { unsafe_func });
        assert!(matches!(result, Ok(2)));
    }

    #[test]
    fn except_catches_raised() {
        let result = catch_exception!(unsafe { raise_exception } => { Error::TypeError });
        assert!(result.is_err());
    }
}
