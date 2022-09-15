use crate::{
    //trezorhal::time::{clear_acc, get_ticks, init_ticks},
    ui::{
        component::{
            text::{paragraphs::Paragraphs, TextStyle},
            Child, Component, Event, EventCtx, Pad,
        },
        constant::screen,
        display,
        display::Color,
        geometry::{LinearPlacement, Offset, Point, Rect},
        model_tt::{
            bootloader::{
                theme::{button_bld_menu, ICON_BG, IMAGE_BG, MENU},
                title::Title,
                ReturnToC,
            },
            theme::{FONT_MEDIUM, FONT_NORMAL},
        },
    },
};
use crate::trezorhal::adc::{get_temp, get_vbat, get_vrefint};
use crate::ui::constant;

use crate::ui::model_tt::{
    bootloader::{theme::IMAGE_HS, title::TitleMsg},
    component::{Button, HoldToConfirm, HoldToConfirmMsg},
    constant::{HEIGHT, WIDTH},
    theme,
    theme::ICON_RECEIVE,
};
use crate::ui::model_tt::theme::IMAGE_ERROR;

#[repr(u32)]
#[derive(Copy, Clone)]
pub enum IntroMsg {
    Menu = 1,
    Host = 2,
}
impl ReturnToC for IntroMsg {
    fn return_to_c(&self) -> u32 {
        *self as u32
    }
}

pub struct Intro {
    bg: Pad,
    title: Child<Title>,
    menu: Child<Button<&'static str>>,
    host: Child<HoldToConfirm<Title>>,
    text: Child<Paragraphs<&'static str>>,
}

impl Intro {
    pub fn new(bld_version: &'static str, vendor: &'static str, version: &'static str) -> Self {
        let style = TextStyle::new(FONT_MEDIUM, theme::FG, theme::BG, theme::FG, theme::FG);
        let p1 = Paragraphs::new()
            .add(style, version)
            .add(style, vendor)
            .with_placement(LinearPlacement::vertical().align_at_start());

        let mut instance = Self {
            bg: Pad::with_background(Color::rgb(0, 0, 0)),
            title: Child::new(Title::new(bld_version)),
            menu: Child::new(Button::with_icon(MENU).styled(button_bld_menu())),
            host: Child::new(HoldToConfirm::new(Title::new("aaa"))),
            text: Child::new(p1),
        };

        instance.bg.clear();
        instance
    }
}

impl Component for Intro {
    type Msg = HoldToConfirmMsg<TitleMsg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg
            .place(Rect::new(Point::new(0, 0), Point::new(WIDTH, HEIGHT)));
        self.title
            .place(Rect::new(Point::new(15, 24), Point::new(180, 40)));
        self.menu.place(Rect::new(
            Point::new(187, 15),
            Point::new(187 + 38, 15 + 38),
        ));
        self.host
            .place(Rect::new(Point::new(0, 0), Point::new(240, 240)));
        self.text
            .place(Rect::new(Point::new(15, 75), Point::new(225, 200)));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        return self.host.event(ctx, event);
    }

    fn paint(&mut self) {
        //self.host.paint();
        //init_ticks();
        // display::rect_fill(screen(), theme::RED);
        // display::icon(Point::new(100,100), ICON_BG, theme::GREEN,
        // theme::RED);
        // display::icon(screen().center(), ICON_BG,
        //theme::GREEN, theme::BLUE);

        // display::icon_rust(screen().
        // center(), ICON_BG, theme::GREEN, theme::BLUE);
        // display::icon_over_icon(
        //     Some(Rect::new(Point::new(0,0), Point::new(240, 240))),
        //     (ICON_BG, Offset::new(-10, -10), theme::GREEN),
        //     (ICON_RECEIVE, Offset::new(30, 30), theme::BLUE),
        //     theme::RED, );

        // let mut buffer = [0_u8;32];

        let s1 = get_vbat();
        let s2 = get_vrefint();
        let s3 = get_temp();

        let a = screen().split_top(30);

        display::text_on_bg(a.0, s1.as_str(), FONT_NORMAL, Offset::new(10, 25), theme::FG, theme::GREY_MEDIUM);
        //display::text(Point::new(10, 30), s1.as_str(), FONT_NORMAL, theme::FG, theme::BG);

        let a = a.1.split_top(30);

        display::text_on_bg(a.0, s2.as_str(), FONT_NORMAL, Offset::new(10, 25), theme::FG, theme::GREY_DARK);

        let a = a.1.split_top(30);
        display::text_on_bg(a.0, s3.as_str(), FONT_NORMAL, Offset::new(10, 25), theme::FG, theme::GREY_MEDIUM);


        //display::text(Point::new(10, 60), s2.as_str(), FONT_NORMAL, theme::FG, theme::BG);


        // display::text_over_image(
        //     Some((Rect::new(Point::new(0,30), Point::new(240, 60)),
        //     theme::BG)),
        //     IMAGE_ERROR,
        //     s2.as_str(),
        //         FONT_NORMAL,
        //     Offset::new(0,0),
        //     Offset::new(10,30),
        //     theme::WHITE,
        // );

        // display::rect_fill(Rect::new(Point::new(0,0), Point::new(240,
        // 240)), // theme::GREEN);

        //display::image(screen().center(), IMAGE_HS);

        //get_ticks();
        //clear_acc();

        // display::text(
        //     screen().bottom_center() + Offset::new(0,-10),
        //     "VrefInt",
        //     FONT_NORMAL,
        //     theme::BLUE,
        //     Color::rgb(0, 0, 0),
        // )
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.menu.bounds(sink);
    }
}
