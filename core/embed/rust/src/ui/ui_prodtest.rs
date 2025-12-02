#[cfg(feature = "touch")]
use crate::ui::{event::TouchEvent, geometry::Rect};
#[cfg(feature = "touch")]
use heapless::Vec;

use crate::ui::component::Event;

pub trait ProdtestLayoutType {
    fn event(&mut self, event: Option<Event>) -> u32;
    fn show(&mut self) -> u32;
    fn init_welcome(id: Option<&'static str>) -> Self;
}

pub trait ProdtestUI {
    type CLayoutType: ProdtestLayoutType;

    fn screen_prodtest_show_text(text: &str);

    fn screen_prodtest_border();

    fn screen_prodtest_nfc(tag_connected: bool);

    fn screen_prodtest_bars(colors: &str);

    #[cfg(feature = "touch")]
    fn screen_prodtest_touch(area: Rect);

    #[cfg(feature = "touch")]
    fn screen_prodtest_draw(events: Vec<TouchEvent, 256>);
}
