use crate::ui::{
    display::{refresh, toif::Toif, Color, Font},
    event::TouchEvent,
    geometry::{Insets, Offset, Point, Rect},
    model_tt::theme::bootloader::{FIRE40, REFRESH24, WARNING40},
    shape,
    shape::Renderer,
};

use qrcodegen::{QrCode, QrCodeEcc, Version};

use crate::{time, trezorhal::io::io_touch_read};
use core::fmt::Write;
use heapless::String;

fn render_screen_1<'a>(target: &mut impl Renderer<'a>, _ctx: &'a DemoContext) {
    let r = Rect::from_top_left_and_size(Point::new(30, 120), Offset::new(180, 60));
    shape::Bar::new(r)
        .with_radius(16)
        .with_bg(Color::rgb(96, 128, 128))
        .render(target);

    let r = Rect::from_top_left_and_size(Point::new(50, 50), Offset::new(50, 50));
    shape::Bar::new(r)
        .with_fg(Color::rgb(128, 0, 192))
        .with_bg(Color::rgb(192, 0, 0))
        .with_thickness(4)
        .render(target);

    let r = Rect::new(Point::zero(), Point::new(16, 160));
    shape::Bar::new(r.translate(Offset::new(140, 40)))
        .with_bg(Color::rgb(0, 160, 0))
        .render(target);

    let pt = Point::new(0, 0);
    shape::Text::new(pt, "TREZOR!!!")
        .with_fg(Color::rgb(255, 0, 0))
        .render(target);

    let pt = Point::new(80, 0);
    shape::Text::new(pt, "TREZOR!!!")
        .with_fg(Color::rgb(0, 255, 0))
        .render(target);

    let pt = Point::new(160, 0);
    shape::Text::new(pt, "TREZOR!!!")
        .with_fg(Color::rgb(0, 0, 255))
        .render(target);

    let pt = Point::new(80, 80);
    shape::Text::new(pt, "BITCOIN!")
        .with_font(Font::BOLD)
        .render(target);

    let pt = Point::new(80, 140);
    let s = "SatoshiLabs";
    shape::Text::new(pt, s)
        .with_fg(Color::rgb(0, 255, 255))
        .render(target);

    shape::Text::new(pt + Offset::new(1, 1), s)
        .with_fg(Color::rgb(255, 0, 0))
        .render(target);

    let pt = Point::new(-1, 40);
    let toif = Toif::new(REFRESH24).unwrap();
    shape::ToifImage::new(pt, toif)
        .with_fg(Color::black())
        .with_bg(Color::white())
        .render(target);

    let pt = Point::new(80, 40);
    let toif = Toif::new(FIRE40).unwrap();
    shape::ToifImage::new(pt, toif).render(target);

    let pt = Point::new(95, 50);
    let toif = Toif::new(WARNING40).unwrap();
    shape::ToifImage::new(pt, toif)
        .with_fg(Color::rgb(64, 192, 200))
        .render(target);

    const ICON_GOOGLE: &[u8] = include_res!("model_tt/res/fido/icon_google.toif");

    let pt = Point::new(0, 70);
    let toif = Toif::new(ICON_GOOGLE).unwrap();
    shape::ToifImage::new(pt, toif).render(target);

    let pt = Point::new(120, 120);
    shape::Circle::new(pt, 20)
        .with_bg(Color::white())
        .render(target);
}

fn draw_screen_2<'a>(target: &mut impl Renderer<'a>) {
    let pt = Point::new(120, 110);
    shape::Circle::new(pt, 60)
        .with_bg(Color::rgb(80, 80, 80))
        .render(target);
    shape::Circle::new(pt, 42)
        .with_bg(Color::rgb(0, 0, 0))
        .with_fg(Color::white())
        .with_thickness(2)
        .render(target);

    let toif = Toif::new(FIRE40).unwrap();
    let icon_tl = Point::new(pt.x - toif.width() / 2, pt.y - toif.height() / 2);
    shape::ToifImage::new(icon_tl, toif).render(target);

    let pt = Point::new(35, 190);
    shape::Text::new(pt, "Installing firmware")
        .with_fg(Color::white())
        .render(target);
}

fn render_screen_3<'a>(target: &mut impl Renderer<'a>) {
    const IMAGE_HOMESCREEN: &[u8] = include_res!("minion.jpg");

    shape::JpegImage::new(Point::new(0, 0), IMAGE_HOMESCREEN)
        .with_scale(0)
        .with_blur(2)
        .render(target);

    let r = Rect::new(Point::new(30, 30), Point::new(100, 70));
    shape::Bar::new(r)
        .with_bg(Color::rgb(0, 255, 0))
        .with_alpha(128)
        .with_radius(10)
        .render(target);
}

fn render_screen_4<'a>(target: &mut impl Renderer<'a>, ctx: &DemoContext) {
    let r = Rect::new(Point::new(30, 30), Point::new(210, 210));
    shape::Bar::new(r)
        .with_bg(Color::white())
        .with_radius(8)
        .render(target);

    if let Some(qr) = ctx.qr {
        shape::QrImage::new(r.inset(Insets::uniform(4)), qr)
            .with_fg(Color::white())
            .with_bg(Color::rgb(80, 0, 0))
            .render(target);
    }
}

fn render_screen_5<'a>(target: &mut impl Renderer<'a>, ctx: &DemoContext) {
    let pt = Point::new(120, 110);
    shape::Circle::new(pt, 60)
        .with_bg(Color::rgb(80, 80, 80))
        .render(target);

    shape::Circle::new(pt, 60)
        .with_end_angle(ctx.counter)
        .with_bg(Color::white())
        .render(target);

    shape::Circle::new(pt, 42)
        .with_bg(Color::rgb(0, 0, 0))
        .with_fg(Color::white())
        .with_thickness(2)
        .render(target);

    let toif = Toif::new(FIRE40).unwrap();
    let icon_tl = Point::new(pt.x - toif.width() / 2, pt.y - toif.height() / 2);
    shape::ToifImage::new(icon_tl, toif).render(target);

    let pt = Point::new(35, 190);
    shape::Text::new(pt, "Installing firmware")
        .with_fg(Color::white())
        .render(target);
}

fn render_screen_6<'a>(target: &mut impl Renderer<'a>, _ctx: &DemoContext) {
    let r = Rect::from_size(Offset::new(40, 40)).translate(Offset::new(10, 10));

    for y in 0..4 {
        for x in 0..4 {
            let radius = x + y * 4;
            let ofs = Offset::new(x * 50, y * 50);
            shape::Bar::new(r.translate(ofs))
                .with_radius(radius)
                .with_bg(Color::white())
                .with_alpha(80)
                .render(target);
        }
    }
}

fn render_demo(ctx: &DemoContext) -> time::Duration {
    let split = ctx.split + ctx.delta;
    let start_time = time::Instant::now();

    shape::render_on_display(
        Some(Rect::new(Point::new(0, 20), Point::new(240, 240))),
        Some(Color::rgb(0, 0, 48)),
        |target| {
            target.with_origin(Offset::new(split.x, split.y), &|target| {
                render_screen_6(target, ctx);
            });

            target.with_origin(Offset::new(split.x - 240, split.y), &|target| {
                render_screen_5(target, ctx);
            });

            target.with_origin(Offset::new(split.x - 480, split.y), &|target| {
                render_screen_4(target, ctx);
            });

            target.with_origin(Offset::new(split.x - 720, split.y), &|target| {
                render_screen_3(target);
            });

            target.with_origin(Offset::new(split.x - 960, split.y), &|target| {
                draw_screen_2(target);
            });

            target.with_origin(Offset::new(split.x - 1200, split.y), &|target| {
                render_screen_1(target, ctx);
            });

            /*let r = Rect::new(Point::new(60, 60), Point::new(180, 180));
            //let r = Rect::new(Point::new(0, 0), Point::new(240, 240));
            //shape::Blurring::new(r, 1).render(&mut target);
            //shape::Blurring::new(r, 2).render(&mut target);
            //shape::Blurring::new(r, 3).render(&mut target);
            shape::Blurring::new(r, 4).render(&mut target);
            shape::Bar::new(r)
                .with_fg(Color::white())
                .render(&mut target);*/
        },
    );

    time::Instant::now()
        .checked_duration_since(start_time)
        .unwrap()
}

fn render_info(duration: time::Duration, evstr: &str) {
    shape::render_on_display(
        Some(Rect::new(Point::zero(), Point::new(240, 20))),
        Some(Color::rgb(0, 0, 255)),
        |target| {
            let text_color = Color::rgb(255, 255, 0);

            let mut info = String::<128>::new();
            write!(info, "{}ms", duration.to_millis() as f32 / 1.0).unwrap();

            let font = Font::NORMAL;
            let pt = Point::new(0, font.vert_center(0, 20, "A"));
            shape::Text::new(pt, info.as_str())
                .with_fg(text_color)
                .with_font(font)
                .render(target);

            let pt = Point::new(60, font.vert_center(0, 20, "A"));
            shape::Text::new(pt, evstr)
                .with_fg(text_color)
                .render(target);
        },
    );
}

struct DemoContext<'a> {
    split: Point,
    origin: Point,
    delta: Offset,
    pressed: bool,
    evstr: String<128>,
    sevstr: String<128>,
    qr: Option<&'a QrCode<'a>>,

    pub counter: i16,
    toif: [u8; 10],
}

impl<'a> DemoContext<'a> {
    fn new(qr: Option<&'a QrCode>) -> Self {
        Self {
            split: Point::zero(),
            origin: Point::zero(),
            delta: Offset::zero(),
            pressed: false,
            evstr: String::<128>::new(),
            sevstr: String::<128>::new(),
            counter: 0,
            qr: qr,
            toif: [0u8; 10],
        }
    }

    fn update(&mut self, event: Option<TouchEvent>) {
        match event {
            Some(TouchEvent::TouchStart(pt)) => {
                self.origin = pt;

                self.evstr.clear();
                self.sevstr.clear();
                write!(self.evstr, "S[{},{}]", pt.x, pt.y).unwrap();
                write!(self.sevstr, "{}  ", self.evstr).unwrap();
            }

            Some(TouchEvent::TouchMove(pt)) => {
                self.evstr.clear();
                write!(self.evstr, "{}", self.sevstr).unwrap();
                write!(self.evstr, "M[{},{}]", pt.x, pt.y).unwrap();

                let delta = pt - self.origin;
                let k = 0;
                self.delta.x = (self.delta.x * k + delta.x * (10 - k)) / 10;
                self.delta.y = (self.delta.y * k + delta.y * (10 - k)) / 10;
            }
            Some(TouchEvent::TouchEnd(pt)) => {
                self.evstr.clear();
                write!(self.evstr, "{}", self.sevstr).unwrap();
                write!(self.evstr, "E[{},{}]", pt.x, pt.y).unwrap();

                self.split = self.split + self.delta;
                self.pressed = false;
                self.delta = Offset::zero();
            }
            None => {
                if self.split.x < 0 {
                    self.split.x -= self.split.x / 4;
                } else if self.split.x > 960 {
                    self.split.x -= (self.split.x - 960) / 4;
                }

                if self.split.y < -120 {
                    self.split.y = -120;
                } else if self.split.y > 120 {
                    self.split.y = 120;
                }
            }
        }
        self.counter += 1;
        if self.counter == 720 {
            self.counter = 0;
        }
    }
}

fn touch_event() -> Option<TouchEvent> {
    let event = io_touch_read();
    if event == 0 {
        return None;
    }
    let event_type = event >> 24;
    let ex = ((event >> 12) & 0xFFF) as i16;
    let ey = (event & 0xFFF) as i16;

    TouchEvent::new(event_type, ex as _, ey as _).ok()
}

#[no_mangle]
extern "C" fn drawlib_demo() {
    const QR_MAX_VERSION: Version = Version::new(10);

    let mut outbuffer = [0u8; QR_MAX_VERSION.buffer_len()];
    let mut tempbuffer = [0u8; QR_MAX_VERSION.buffer_len()];

    let qr = unwrap!(QrCode::encode_text(
        "https://satoshilabs.com",
        &mut tempbuffer,
        &mut outbuffer,
        QrCodeEcc::Medium,
        Version::MIN,
        QR_MAX_VERSION,
        None,
        true,
    ));

    let mut ctx = DemoContext::new(Some(&qr));

    loop {
        ctx.update(touch_event());

        let duration = render_demo(&ctx);
        render_info(duration, ctx.evstr.as_str());

        refresh();
    }
}
