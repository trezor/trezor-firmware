#![forbid(unsafe_code)]

pub mod base;
pub mod border;
pub mod connect;
pub mod empty;
pub mod image;
pub mod label;
pub mod map;
pub mod marquee;
pub mod maybe;
pub mod pad;
pub mod paginated;
pub mod painter;
pub mod placed;
pub mod qr_code;
pub mod text;
pub mod timeout;

pub use base::{Child, Component, ComponentExt, Event, EventCtx, Never, Root, TimerToken};
pub use border::Border;
pub use empty::Empty;
pub use label::Label;
pub use map::MsgMap;
pub use marquee::Marquee;
pub use maybe::Maybe;
pub use pad::Pad;
pub use paginated::{PageMsg, Paginate};
pub use painter::Painter;
pub use placed::{FixedHeightBar, Floating, GridPlaced, Split};
pub use qr_code::Qr;
pub use text::{
    formatted::FormattedText,
    layout::{LineBreaking, PageBreaking, TextLayout},
};
pub use timeout::Timeout;
