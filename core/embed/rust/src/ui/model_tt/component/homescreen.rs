use crate::ui::component::{Component, Event, EventCtx, Pad};
use crate::ui::constant::screen;
use crate::ui::display;
use crate::ui::event::TouchEvent;
use crate::ui::geometry::{Point, Rect};
use crate::ui::model_tt::component::PinKeyboard;
use crate::ui::model_tt::theme;

pub enum BootState {
    NotInitialized,
    NotConnected,
    PinEntry,
    Locked,
}



pub struct Homescreen {
    pad: Pad,
    pin: PinKeyboard<&'static str>,
    boot_state: BootState,
    device_name: &'static str,
}




pub enum HomescreenMsg {
    Finished,
}

impl Homescreen {
    pub fn new() -> Self {

        let mut pin = PinKeyboard::new(
            "Enter Pin M",
            "Enter Pin",
            None,
            true,
        );

        let mut instance = Self {
            pad: Pad::with_background(theme::BG),
            pin,
            boot_state: BootState::NotConnected,
            device_name: "My Trezor",
        };

        instance.pad.clear();
        instance
    }

    pub fn paint_not_connected(&self) {
        display::avatar(screen().center(), theme::IMAGE_HOMESCREEN, theme::WHITE, theme::BLACK);

        display::text_center(Point::new(screen().center().x, 35),"My Trezor",theme::FONT_BOLD, theme::GREY_LIGHT, theme::BG);

        // ui.display.text_center(
        //     ui.WIDTH // 2, 35, self.label, ui.BOLD, ui.TITLE_GREY, ui.BG
        // )
        // ui.display.avatar(48, 48, self.get_image(), ui.WHITE, ui.BLACK)

        // # lock bar

        let bar_area = Rect::new(Point::new(40, 100), Point::new(200, 140));
        let bar_area_in = Rect::new(Point::new(42, 102), Point::new(198, 138));

        display::rect_fill_rounded(
            bar_area, theme::GREY_LIGHT, theme::BG, 4);

        display::rect_fill_rounded(
            bar_area_in, theme::BG, theme::GREY_LIGHT, 4);


        // ui.display.text_center(
        //     ui.WIDTH // 2, 128, self.lock_label, ui.BOLD, ui.TITLE_GREY, ui.BG
        // )
        //
        // # "tap to unlock"
        // ui.display.text_center(
        //     ui.WIDTH // 2 + 10, 220, self.tap_label, ui.BOLD, ui.TITLE_GREY, ui.BG
        // )
        // ui.display.icon(45, 202, res.load(ui.ICON_CLICK), ui.TITLE_GREY, ui.BG)
    }
}

impl Component for Homescreen {
    type Msg = HomescreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.pad.place(bounds);
        self.pin.place(bounds);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {

        match self.boot_state {
            BootState::NotConnected => {
                if let Event::Touch(TouchEvent::TouchEnd(pos)) = event {
                    self.pad.clear();
                    ctx.request_paint();
                    self.boot_state = BootState::PinEntry;
                }
                None
            }
            BootState::NotInitialized => {None}
            BootState::PinEntry => {
                self.pin.event(ctx, event);
                None
            }
            BootState::Locked => {None}
        }
    }

    fn paint(&mut self) {
        self.pad.paint();
        //self.paint_uninitialized();
        match self.boot_state {
            BootState::NotConnected => { self.paint_not_connected() }
            BootState::NotInitialized => {}
            BootState::PinEntry => {self.pin.paint()}
            BootState::Locked => {}
        }
    }

    fn bounds(&self, _sink: &mut dyn FnMut(Rect)) {

    }
}
