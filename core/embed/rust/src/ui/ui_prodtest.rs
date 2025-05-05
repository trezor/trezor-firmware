#[cfg(feature = "touch")]
use crate::ui::event::TouchEvent;
#[cfg(feature = "touch")]
use heapless::Vec;

use crate::ui::{component::Event, geometry::Rect};

pub trait ProdtestUI {
    fn screen_prodtest_event(buf: &mut [u8], event: Option<Event>) -> u32;

    fn screen_prodtest_welcome(buf: &mut [u8], id: Option<&'static str>);

    fn screen_prodtest_show_text(text: &str);

    fn screen_prodtest_border();

    fn screen_prodtest_bars(colors: &str);

    #[cfg(feature = "touch")]
    fn screen_prodtest_touch(area: Rect);

    #[cfg(feature = "touch")]
    fn screen_prodtest_draw(events: Vec<TouchEvent, 256>);
}
