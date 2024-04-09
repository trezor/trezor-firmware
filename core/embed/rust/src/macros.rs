macro_rules! unwrap {
    ($e:expr, $msg:expr) => {{
        use $crate::trezorhal::fatal_error::UnwrapOrFatalError;
        $e.unwrap_or_fatal_error($msg, file!(), line!())
    }};
    ($expr:expr) => {
        unwrap!($expr, "unwrap failed")
    };
}

macro_rules! ensure {
    ($what:expr, $error:expr) => {
        if !($what) {
            $crate::trezorhal::fatal_error::__fatal_error($error, file!(), line!());
        }
    };
}

macro_rules! fatal_error {
    ($msg:expr) => {{
        $crate::trezorhal::fatal_error::__fatal_error($msg, file!(), line!());
    }};
}

// from https://docs.rs/ufmt/latest/ufmt/
// like `std::format!` it returns a `heapless::String` but uses `uwrite!`
// instead of `write!`
macro_rules! uformat {
    // IMPORTANT use `tt` fragments instead of `expr` fragments (i.e. `$($exprs:expr),*`)
    (@$type:ty, $($tt:tt)*) => {{
        let mut s = <$type>::new();
        unwrap!(ufmt::uwrite!(&mut s, $($tt)*));
        s
    }};
    (len:$len:expr, $($tt:tt)*) => {
        uformat!(@heapless::String::<$len>, $($tt)*)
    };
    ($($tt:tt)*) => {
        uformat!(@crate::strutil::ShortString, $($tt)*)
    };
}

#[allow(unused_macros)] // Should be used only for debugging purposes
macro_rules! dbg_print {
    ($($args:tt)*) => {
        #[cfg(feature = "debug")]
        ufmt::uwrite!($crate::debug::DebugConsole, $($args)*).ok();
    }
}

#[allow(unused_macros)] // Should be used only for debugging purposes
macro_rules! dbg_println {
    ($($args:tt)*) => {
        #[cfg(feature = "debug")]
        ufmt::uwriteln!($crate::debug::DebugConsole, $($args)*).ok();
    }
}
