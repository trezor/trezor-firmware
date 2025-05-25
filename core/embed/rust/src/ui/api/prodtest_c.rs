use crate::{
    trezorhal::{
        layout_buf::{c_layout_t, LayoutBuffer},
        sysevent::{parse_event, sysevents_t},
    },
    ui::{
        ui_prodtest::{ProdtestLayoutType, ProdtestUI},
        ModelUI,
    },
    util::from_c_array,
};

#[cfg(feature = "touch")]
use crate::ui::geometry::{Offset, Point, Rect};
#[cfg(feature = "touch")]
use crate::ui::{event::TouchEvent, layout::simplified::touch_unpack};
#[cfg(feature = "touch")]
use cty::int16_t;
#[cfg(feature = "touch")]
use heapless::Vec;

#[no_mangle]
extern "C" fn screen_prodtest_event(layout: *mut c_layout_t, signalled: &sysevents_t) -> u32 {
    let e = parse_event(signalled);
    // SAFETY: calling code is supposed to give us exclusive access to an already
    // initialized layout
    unsafe {
        let mut layout = LayoutBuffer::<<ModelUI as ProdtestUI>::CLayoutType>::new(layout);
        let layout = layout.get_mut();
        layout.event(e)
    }
}

#[no_mangle]
extern "C" fn screen_prodtest_welcome(layout: *mut c_layout_t, id: *const cty::c_char, id_len: u8) {
    let id = if id.is_null() {
        None
    } else {
        unsafe { from_c_array(id, id_len as usize) }
    };

    let mut screen = <ModelUI as ProdtestUI>::CLayoutType::init_welcome(id);
    screen.show();
    // SAFETY: calling code is supposed to give us exclusive access to the layout
    let mut layout = unsafe { LayoutBuffer::new(layout) };
    layout.store(screen);
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

#[no_mangle]
#[cfg(feature = "touch")]
extern "C" fn screen_prodtest_draw(events: *const cty::uint32_t, events_len: u32) {
    let events = unsafe { core::slice::from_raw_parts(events, events_len as usize) };

    let mut v: Vec<TouchEvent, 256> = Vec::new();

    for e in events.iter() {
        if let Some(event) = touch_unpack(*e) {
            unwrap!(v.push(event));
        }
    }

    ModelUI::screen_prodtest_draw(v);
}
