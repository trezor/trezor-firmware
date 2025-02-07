use crate::ui::geometry::Rect;

pub trait ProdtestUI {
    fn screen_prodtest_welcome();

    fn screen_prodtest_info(id: &str, date: &str);

    fn screen_prodtest_show_text(text: &str);

    fn screen_prodtest_border();

    fn screen_prodtest_bars(colors: &str);

    fn screen_prodtest_touch(area: Rect);
}
