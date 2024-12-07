//#![forbid(unsafe_code)]

pub mod bar;
pub mod base;
pub mod border;
pub mod button_request;
#[cfg(all(feature = "jpeg", feature = "ui_image_buffer", feature = "micropython"))]
pub mod cached_jpeg;
pub mod connect;
pub mod empty;
pub mod image;
#[cfg(all(feature = "jpeg", feature = "micropython"))]
pub mod jpeg;
pub mod label;
pub mod map;
pub mod marquee;
pub mod maybe;
pub mod pad;
pub mod paginated;
pub mod placed;
pub mod qr_code;
#[cfg(feature = "touch")]
pub mod swipe;
#[cfg(feature = "touch")]
pub mod swipe_detect;
pub mod text;
pub mod timeout;

pub use bar::Bar;
pub use base::{Child, Component, ComponentExt, Event, EventCtx, FlowMsg, Never, Timer};
pub use border::Border;
pub use button_request::{ButtonRequestExt, SendButtonRequest};
#[cfg(all(feature = "jpeg", feature = "ui_image_buffer", feature = "micropython"))]
pub use cached_jpeg::CachedJpeg;
pub use empty::Empty;
#[cfg(all(feature = "jpeg", feature = "micropython"))]
pub use jpeg::Jpeg;
pub use label::Label;
pub use map::{MsgMap, PageMap};
pub use marquee::Marquee;
pub use maybe::Maybe;
pub use pad::Pad;
pub use paginated::{PageMsg, Paginate};
pub use placed::{FixedHeightBar, Floating, GridPlaced, Split};
pub use qr_code::Qr;
#[cfg(feature = "touch")]
pub use swipe::Swipe;
#[cfg(feature = "touch")]
pub use swipe_detect::SwipeDetect;
pub use text::{
    formatted::FormattedText,
    layout::{LineBreaking, PageBreaking, TextLayout},
};
pub use timeout::Timeout;
