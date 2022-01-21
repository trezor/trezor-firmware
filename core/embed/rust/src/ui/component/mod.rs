#![forbid(unsafe_code)]

pub mod base;
pub mod empty;
pub mod label;
pub mod map;
pub mod pad;
pub mod paginated;
pub mod text;
pub mod tuple;

pub use base::{Child, Component, ComponentExt, Event, EventCtx, Never, TimerToken};
pub use empty::Empty;
pub use label::{Label, LabelStyle};
pub use map::Map;
pub use pad::Pad;
pub use paginated::{PageMsg, Paginate};
pub use text::{
    formatted::FormattedText,
    layout::{LineBreaking, PageBreaking, TextLayout},
};
