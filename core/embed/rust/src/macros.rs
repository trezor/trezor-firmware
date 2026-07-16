// from https://docs.rs/ufmt/latest/ufmt/
// like `std::format!` it returns a `heapless::String` but uses `uwrite!`
// instead of `write!`
#[allow(unused_macros)]
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
