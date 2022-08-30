#![forbid(unsafe_code)]

pub mod base;
pub mod border;
pub mod empty;
pub mod image;
pub mod label;
pub mod map;
pub mod maybe;
pub mod pad;
pub mod paginated;
pub mod painter;
pub mod placed;
pub mod text;
pub mod timeout;

pub use base::{Child, Component, ComponentExt, Event, EventCtx, Never, TimerToken};
pub use border::Border;
pub use empty::Empty;
pub use image::Image;
pub use label::{Label, LabelStyle};
pub use map::Map;
pub use maybe::Maybe;
pub use pad::Pad;
pub use paginated::{PageMsg, Paginate};
pub use painter::{qrcode_painter, Painter};
pub use placed::{FixedHeightBar, GridPlaced};
pub use text::{
    formatted::FormattedText,
    layout::{LineBreaking, PageBreaking, TextLayout},
};
pub use timeout::{Timeout, TimeoutMsg};
