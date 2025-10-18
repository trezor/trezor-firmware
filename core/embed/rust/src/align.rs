// taken from: https://users.rust-lang.org/t/can-i-conveniently-compile-bytes-into-a-rust-program-with-a-specific-alignment/24049/2

#[repr(C)]
pub struct AlignedTo<Align, Bytes: ?Sized> {
    pub _align: [Align; 0],
    pub data: Bytes,
}

macro_rules! include_aligned {
    ($align:ty, $filename:expr) => {{
        use $crate::align::AlignedTo;

        static ALIGNED: &AlignedTo<$align, [u8]> = &AlignedTo {
            _align: [],
            data: *include_bytes!($filename),
        };

        &ALIGNED.data
    }};
}
pub(crate) use include_aligned;
