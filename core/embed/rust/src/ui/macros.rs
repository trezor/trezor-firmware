#[allow(unused_macros)] // T1 doesn't use icons (yet)
macro_rules! include_res {
    ($filename:expr) => {
        include_bytes!(concat!(env!("CARGO_MANIFEST_DIR"), "/src/ui/", $filename))
    };
}

#[allow(unused_macros)] // Only used in TR so far.
/// Concatenates arbitrary amount of slices into a String.
macro_rules! build_string {
    ($max:expr, $($string:expr),+) => {
        {
            let mut new_string = String::<$max>::new();
            $(unwrap!(new_string.push_str($string));)+
            new_string
        }
    }
}

#[cfg(feature = "ui_debug")]
/// Transforms integer into string slice. For example for printing.
macro_rules! inttostr {
    ($int:expr) => {{
        heapless::String::<10>::from($int).as_str()
    }};
}
