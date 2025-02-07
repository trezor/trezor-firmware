use crate::ui::{ui_prodtest::ProdtestUI, util::from_c_array, ModelUI};

#[cfg(feature = "touch")]
use crate::ui::geometry::{Offset, Point, Rect};
#[cfg(feature = "touch")]
use cty::int16_t;

#[no_mangle]
extern "C" fn screen_prodtest_welcome() {
    ModelUI::screen_prodtest_welcome();
}

#[no_mangle]
extern "C" fn screen_prodtest_info(
    id: *const cty::c_char,
    id_len: u8,
    date: *const cty::c_char,
    date_len: u8,
) {
    let id = unwrap!(unsafe { from_c_array(id, id_len as usize) });
    let date = unwrap!(unsafe { from_c_array(date, date_len as usize) });

    ModelUI::screen_prodtest_info(id, date);
}

#[no_mangle]
extern "C" fn screen_prodtest_show_text(text: *const cty::c_char, text_len: u8) {
    let text = unwrap!(unsafe { from_c_array(text, text_len as usize) });

    ModelUI::screen_prodtest_show_text(text);
}

#[no_mangle]
extern "C" fn screen_prodtest_border() {
    ModelUI::screen_prodtest_border();
}

#[no_mangle]
extern "C" fn screen_prodtest_bars(colors: *const cty::c_char, colors_len: u8) {
    let colors: &str = unwrap!(unsafe { from_c_array(colors, colors_len as usize) });
    ModelUI::screen_prodtest_bars(colors);
}

#[no_mangle]
#[cfg(feature = "touch")]
extern "C" fn screen_prodtest_touch(x0: int16_t, y0: int16_t, w: int16_t, h: int16_t) {
    let area = Rect::from_top_left_and_size(Point::new(x0, y0), Offset::new(w, h));
    ModelUI::screen_prodtest_touch(area);
}
