#[cfg(feature = "touch")]
use crate::ui::event::TouchEvent;
use crate::ui::geometry::Rect;
#[cfg(feature = "touch")]
use heapless::Vec;

pub trait ProdtestUI {
    fn screen_prodtest_welcome();

    fn screen_prodtest_info(id: &str);

    fn screen_prodtest_show_text(text: &str);

    fn screen_prodtest_border();

    fn screen_prodtest_bars(colors: &str);

    #[cfg(feature = "touch")]
    fn screen_prodtest_touch(area: Rect);

    #[cfg(feature = "touch")]
    fn screen_prodtest_draw(events: Vec<TouchEvent, 256>);
}
